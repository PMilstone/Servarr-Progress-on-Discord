"""
qBittorrent Discord Webhook Service
Version: 1.2.1
Build: 2026-04-30 1:30 PM EST
"""

import os
import threading
import time
import logging
from logging.handlers import RotatingFileHandler
import datetime
import signal
import sys
import argparse
from pathlib import Path
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from src.qb_client import QBClient
from src.graph import make_embed
from src.discord_webhook import send_embed

# Version Information
VERSION = "1.2.1"
BUILD_DATE = "2026-04-30 1:30 PM EST"

# Mock test data for --test mode
MOCK_ACTIVE_TORRENTS = [
    {
        "name": "Ubuntu.22.04.3.LTS.Desktop.amd64.iso",
        "progress": 0.65,
        "dlspeed": 5500000,  # 5.5 MB/s
        "ulspeed": 125000,   # 125 kB/s
        "eta": 450,          # 7.5 minutes
        "added_on": 1714000000,
        "time_active": 300,  # 5 minutes
        "size": 3500000000,
        "state": "downloading"
    },
    {
        "name": "Debian.12.5.0.amd64.netinst.iso",
        "progress": 0.92,
        "dlspeed": 2300000,  # 2.3 MB/s
        "ulspeed": 50000,    # 50 kB/s
        "eta": 120,          # 2 minutes
        "added_on": 1713990000,
        "time_active": 1800, # 30 minutes
        "size": 650000000,
        "state": "downloading"
    }
]

MOCK_COMPLETED_TORRENTS = [
    {
        "name": "Fedora.Workstation.39.x86_64.iso",
        "completion_on": 1714350000,
        "size": 2100000000
    },
    {
        "name": "Arch.Linux.2024.04.01.x86_64.iso",
        "completion_on": 1714340000,
        "size": 850000000
    },
    {
        "name": "Linux.Mint.21.3.Cinnamon.64bit.iso",
        "completion_on": 1714330000,
        "size": 2800000000
    }
]

# Constants
DEFAULT_PORT = 8383
DEFAULT_UPDATE_INTERVAL = 6
DEFAULT_QB_URL = "http://127.0.0.1:8080"
MIN_UPDATE_INTERVAL = 1
DEFAULT_LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB in bytes

# Load environment early for logging configuration
load_dotenv()

# Configure logging with UTF-8 encoding and rotating file handler
log_max_size = int(os.getenv('LOG_MAX_SIZE', DEFAULT_LOG_MAX_SIZE))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'qbitdiscord.log',
            maxBytes=log_max_size,
            backupCount=3,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress Flask development server warning
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# ANSI color codes
RED = '\033[91m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
RESET = '\033[0m'

# Console color helpers
def print_error(msg: str) -> None:
    """Print error message in red."""
    print(f"{RED}{msg}{RESET}")

def print_warning(msg: str) -> None:
    """Print warning message in yellow."""
    print(f"{YELLOW}{msg}{RESET}")

def print_success(msg: str) -> None:
    """Print success message in green."""
    print(f"{GREEN}{msg}{RESET}")

app = Flask(__name__)
_active_monitor_thread = None
_active_monitor_lock = threading.Lock()
_last_update_time = None
_last_update_status = None
_shutdown_flag = threading.Event()
_use_test_data = False  # Global flag for test mode

class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass

def signal_handler(sig, frame):
    """Handle graceful shutdown on SIGINT or SIGTERM."""
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    _shutdown_flag.set()
    sys.exit(0)

def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def validate_config(cfg: dict) -> None:
    """Validate configuration values and raise ConfigError if invalid."""
    errors = []
    
    # Check for required WEBHOOK_URL
    webhook_url = cfg.get("WEBHOOK_URL")
    if not webhook_url:
        errors.append(
            "WEBHOOK_URL is required but not set.\n"
            "    → Create a .env file in the project root\n"
            "    → Add: WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL\n"
            "    → Get webhook URL from Discord: Server Settings → Integrations → Webhooks"
        )
    elif not webhook_url.startswith("https://discord.com/api/webhooks/"):
        errors.append(
            f"WEBHOOK_URL has invalid format: {webhook_url[:50]}...\n"
            "    → Must start with 'https://discord.com/api/webhooks/'\n"
            "    → Example: https://discord.com/api/webhooks/123456789/abcdefg"
        )
    
    # Validate PORT
    port = cfg.get("PORT")
    if not isinstance(port, int) or port < 1 or port > 65535:
        errors.append(
            f"PORT must be between 1 and 65535, got: {port}\n"
            "    → Check PORT value in .env file\n"
            "    → Default is 8383 if not specified"
        )
    
    # Validate ACTIVE_UPDATE_INTERVAL
    interval = cfg.get("ACTIVE_UPDATE_INTERVAL")
    if not isinstance(interval, int) or interval < 1:
        errors.append(
            f"ACTIVE_UPDATE_INTERVAL must be >= 1 second, got: {interval}\n"
            "    → Check ACTIVE_UPDATE_INTERVAL value in .env file\n"
            "    → Recommended: 6 (updates every 6 seconds)"
        )
    
    # Validate QB_URL format
    qb_url = cfg.get("QB_URL")
    if qb_url and not (qb_url.startswith("http://") or qb_url.startswith("https://")):
        errors.append(
            f"QB_URL has invalid format: {qb_url}\n"
            "    → Must start with http:// or https://\n"
            "    → Example: http://127.0.0.1:8080 or http://192.168.1.100:8080"
        )
    
    if errors:
        raise ConfigError(
            "\n" + "=" * 70 + "\n"
            "Configuration Error\n"
            "=" * 70 + "\n\n"
            + "\n\n".join(errors) +
            "\n\n" + "=" * 70 + "\n"
        )

def load_config():
    # Check if .env file exists
    if not Path(".env").exists():
        logger.warning(
            "No .env file found. Using environment variables and defaults.\n"
            "To create .env file:\n"
            "  1. Copy .env.example to .env\n"
            "  2. Edit .env with your Discord webhook URL and qBittorrent settings"
        )
    
    load_dotenv()
    cfg = {
        "WEBHOOK_URL": os.getenv("WEBHOOK_URL"),
        "PORT": int(os.getenv("PORT", DEFAULT_PORT)),
        "ACTIVE_UPDATE_INTERVAL": int(os.getenv("ACTIVE_UPDATE_INTERVAL", DEFAULT_UPDATE_INTERVAL)),
        "QB_URL": os.getenv("QB_URL", DEFAULT_QB_URL),
        "QB_USER": os.getenv("QB_USER"),
        "QB_PASS": os.getenv("QB_PASS"),
        "QB_CATEGORIES": os.getenv("QB_CATEGORIES"),  # None by default means no filtering
        "MESSAGE": os.getenv("MESSAGE"),
        "MESSAGE_ID": os.getenv("MESSAGE_ID"),
        "EMBED_SHOW_DOWNLOAD_SPEED": _env_bool("EMBED_SHOW_DOWNLOAD_SPEED", False),
        "EMBED_SHOW_UPLOAD_SPEED": _env_bool("EMBED_SHOW_UPLOAD_SPEED", False),
        "EMBED_SHOW_ETA": _env_bool("EMBED_SHOW_ETA", True),
        "EMBED_SHOW_TIME_ADDED": _env_bool("EMBED_SHOW_TIME_ADDED", False),
        "EMBED_SHOW_TIME_SINCE_STARTED": _env_bool("EMBED_SHOW_TIME_SINCE_STARTED", False),
    }
    validate_config(cfg)
    return cfg

def run_status_update(cfg: dict, use_test_data: bool = False) -> bool:
    global _last_update_time, _last_update_status
    
    try:
        if use_test_data:
            # Use mock data for testing
            active_torrents = MOCK_ACTIVE_TORRENTS
            completed_torrents = MOCK_COMPLETED_TORRENTS
            logger.info("Using test data (--test mode)")
            print("Using mock Linux distro torrents for testing")
        else:
            # Parse categories from config (None means no filtering)
            categories = None
            if cfg.get("QB_CATEGORIES"):
                categories = [cat.strip() for cat in cfg["QB_CATEGORIES"].split(",")]
            
            with QBClient(cfg["QB_URL"], cfg.get("QB_USER"), cfg.get("QB_PASS"), categories) as qb:
                if not qb.login():
                    qb_url = cfg["QB_URL"]
                    has_creds = bool(cfg.get("QB_USER"))
                    error_msg = (
                        f"\n{'=' * 70}\n"
                        f"qBittorrent Login Failed\n"
                        f"{'=' * 70}\n"
                        f"URL: {qb_url}\n"
                        f"Credentials provided: {'Yes' if has_creds else 'No'}\n\n"
                        f"Troubleshooting steps:\n"
                        f"  1. Check if qBittorrent is running\n"
                        f"  2. Verify qBittorrent Web UI is accessible at {qb_url}\n"
                        f"  3. Check if Web UI is enabled: Options → Web UI → Enable\n"
                    )
                    if has_creds:
                        error_msg += (
                            f"  4. Verify QB_USER and QB_PASS in .env match Web UI credentials\n"
                            f"  5. Check if 'Bypass authentication for localhost' is enabled\n"
                        )
                    else:
                        error_msg += (
                            f"  4. If Web UI requires login, add QB_USER and QB_PASS to .env\n"
                            f"  5. Or enable 'Bypass authentication for localhost' in qBittorrent\n"
                        )
                    error_msg += f"{'=' * 70}\n"
                    raise RuntimeError(error_msg)

                active_torrents = qb.get_active_torrents()
                completed_torrents = qb.get_recent_completed_torrents(5)

        embed_options = {
            "show_download_speed": cfg.get("EMBED_SHOW_DOWNLOAD_SPEED", False),
            "show_upload_speed": cfg.get("EMBED_SHOW_UPLOAD_SPEED", False),
            "show_eta": cfg.get("EMBED_SHOW_ETA", True),
            "show_time_added": cfg.get("EMBED_SHOW_TIME_ADDED", False),
            "show_time_since_started": cfg.get("EMBED_SHOW_TIME_SINCE_STARTED", False),
        }
        embed = make_embed(active_torrents, completed_torrents, embed_options, is_test_mode=use_test_data)
        
        # Send embed using MESSAGE_ID from config if provided
        message_id = cfg.get("MESSAGE_ID")
        send_embed(cfg["WEBHOOK_URL"], embed, cfg.get("MESSAGE"), message_id)
        
        _last_update_time = datetime.datetime.now()
        _last_update_status = "success"
        return len(active_torrents) > 0
    except Exception as e:
        _last_update_status = f"error: {str(e)}"
        raise

def _extract_item_title(payload: dict) -> str:
    if isinstance(payload.get("series"), dict) and payload["series"].get("title"):
        return str(payload["series"]["title"])
    if isinstance(payload.get("movie"), dict) and payload["movie"].get("title"):
        return str(payload["movie"]["title"])
    if isinstance(payload.get("release"), dict) and payload["release"].get("releaseTitle"):
        return str(payload["release"]["releaseTitle"])
    if payload.get("title"):
        return str(payload["title"])
    return "Unknown item"

def _monitor_active_downloads() -> None:
    # Load config once at thread start
    cfg = load_config()
    
    while not _shutdown_flag.is_set():
        if not cfg.get("WEBHOOK_URL"):
            logger.info("Monitor stopping: WEBHOOK_URL not configured")
            break

        try:
            has_active = run_status_update(cfg, use_test_data=_use_test_data)
        except Exception as e:
            msg = f"Active download monitor error: {e}"
            logger.error(msg)
            print(msg)
            break

        if not has_active:
            logger.info("Monitor stopping: No active downloads")
            break

        interval = max(MIN_UPDATE_INTERVAL, int(cfg.get("ACTIVE_UPDATE_INTERVAL", DEFAULT_UPDATE_INTERVAL)))
        # Use wait instead of sleep so we can be interrupted by shutdown flag
        _shutdown_flag.wait(timeout=interval)

def ensure_active_monitor_running() -> None:
    global _active_monitor_thread
    with _active_monitor_lock:
        if _active_monitor_thread and _active_monitor_thread.is_alive():
            return
        _active_monitor_thread = threading.Thread(target=_monitor_active_downloads, daemon=True)
        _active_monitor_thread.start()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat()
    }), 200

@app.route('/status', methods=['GET'])
def status():
    """Status endpoint with detailed information."""
    cfg = load_config()
    
    status_info = {
        "service": "qbitdiscord",
        "version": VERSION,
        "build_date": BUILD_DATE,
        "status": "running",
        "timestamp": datetime.datetime.now().isoformat(),
        "config": {
            "webhook_configured": bool(cfg.get("WEBHOOK_URL")),
            "qb_url": cfg.get("QB_URL"),
            "port": cfg.get("PORT"),
            "update_interval": cfg.get("ACTIVE_UPDATE_INTERVAL"),
        },
        "monitor": {
            "thread_active": _active_monitor_thread is not None and _active_monitor_thread.is_alive() if _active_monitor_thread else False,
            "last_update_time": _last_update_time.isoformat() if _last_update_time else None,
            "last_update_status": _last_update_status,
        }
    }
    
    return jsonify(status_info), 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    cfg = load_config()
    if not cfg["WEBHOOK_URL"]:
        return jsonify({"error": "WEBHOOK_URL not set"}), 500

    if request.method == 'GET':
        return jsonify({"status": "ok"}), 200

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "ignored", "reason": "no json payload"}), 200

    event_type = (data.get("eventType") or data.get("eventtype") or "").strip()
    item_title = _extract_item_title(data)
    msg = f"Webhook received: event={event_type or 'unknown'} item={item_title}"
    logger.info(msg)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

    # Handle any Sonarr/Radarr webhook request so new requests are not missed.
    # Keep a tiny ignore list for obvious non-event probes.
    if event_type.lower() in {"ping", "healthcheck"}:
        return jsonify({"status": "ignored", "event": event_type}), 200

    try:
        # For "Grab" events, delay to give qBittorrent time to process the torrent
        # Sonarr/Radarr send the grab webhook immediately when they send the torrent,
        # but qBittorrent needs a moment to add it to the queue
        if event_type.lower() == "grab":
            logger.info("Grab event detected - waiting 3 seconds for qBittorrent to process torrent")
            time.sleep(3)
        
        has_active = run_status_update(cfg, use_test_data=_use_test_data)
        if has_active:
            ensure_active_monitor_running()
        return jsonify({"status": "updated", "active": has_active, "event": event_type or "unknown"}), 200
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='qBittorrent Discord Webhook Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Version {VERSION} - {BUILD_DATE}"
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run with mock Linux distro torrent data (no qBittorrent connection required)'
    )
    args = parser.parse_args()
    
    # Store test mode flag for monitoring thread
    _use_test_data = args.test
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Display version information
    print("=" * 60)
    print(f"qBittorrent Discord Webhook Service")
    print(f"Version: {VERSION}")
    print(f"Build: {BUILD_DATE}")
    if args.test:
        print(f"Mode: TEST (using mock data)")
    print("=" * 60)
    logger.info(f"Starting service - Version {VERSION}, Build {BUILD_DATE}")
    if args.test:
        logger.info("Running in TEST mode with mock data")
    
    try:
        cfg = load_config()
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        print_error(f"Configuration error: {e}")
        exit(1)
    
    msg = f"Starting webhook server on port {cfg['PORT']}"
    logger.info(msg)
    print(msg)
    
    if cfg.get("WEBHOOK_URL"):
        try:
            has_active = run_status_update(cfg, use_test_data=args.test)
            if has_active:
                ensure_active_monitor_running()
            msg = "Startup status check completed successfully."
            logger.info(msg)
            print_success(msg)
        except Exception as e:
            # Log error but continue - qBittorrent might be offline temporarily
            logger.warning(f"Startup status check failed: {e}")
            logger.warning("Server will still start. qBittorrent connection will be retried on webhook events.")
            print_warning(f"WARNING: Could not connect to qBittorrent at startup")
            print_warning(f"  Reason: {e}")
            print_warning(f"  Troubleshooting:")
            print_warning(f"    - Check if qBittorrent is running")
            print_warning(f"    - Verify QB_URL setting: {cfg['QB_URL']}")
            print_warning(f"    - Check username/password if required")
            print_warning(f"  Server will continue starting and retry on webhook events.")
    else:
        msg = "Startup status check skipped: WEBHOOK_URL not set."
        logger.warning(msg)
        print(msg)
    
    app.run(host='0.0.0.0', port=cfg['PORT'])
