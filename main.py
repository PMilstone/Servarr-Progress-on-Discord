"""
qBittorrent Discord Webhook Service
Version: 1.1.0
Build: 2026-04-28 12:17 EST
"""

import os
import threading
import time
import logging
import json
import datetime
import signal
import sys
from pathlib import Path
from typing import Optional
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from src.qb_client import QBClient
from src.graph import make_embed
from src.discord_webhook import send_embed

# Version Information
VERSION = "1.1.0"
BUILD_DATE = "2026-04-28 12:17 EST"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qbitdiscord.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress Flask development server warning
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Constants
DEFAULT_PORT = 5000
DEFAULT_UPDATE_INTERVAL = 15
DEFAULT_QB_URL = "http://127.0.0.1:8080"
MIN_UPDATE_INTERVAL = 1
MESSAGE_ID_FILE = "message_id.json"

app = Flask(__name__)
_active_monitor_thread = None
_active_monitor_lock = threading.Lock()
_last_update_time = None
_last_update_status = None
_shutdown_flag = threading.Event()

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
    
    # Validate PORT
    port = cfg.get("PORT")
    if not isinstance(port, int) or port < 1 or port > 65535:
        errors.append(f"PORT must be between 1 and 65535, got: {port}")
    
    # Validate ACTIVE_UPDATE_INTERVAL
    interval = cfg.get("ACTIVE_UPDATE_INTERVAL")
    if not isinstance(interval, int) or interval < 1:
        errors.append(f"ACTIVE_UPDATE_INTERVAL must be >= 1, got: {interval}")
    
    # Validate WEBHOOK_URL format (basic check)
    webhook_url = cfg.get("WEBHOOK_URL")
    if webhook_url and not webhook_url.startswith("https://discord.com/api/webhooks/"):
        errors.append(f"WEBHOOK_URL must start with 'https://discord.com/api/webhooks/', got: {webhook_url[:50]}...")
    
    # Validate QB_URL format
    qb_url = cfg.get("QB_URL")
    if qb_url and not (qb_url.startswith("http://") or qb_url.startswith("https://")):
        errors.append(f"QB_URL must start with http:// or https://, got: {qb_url}")
    
    if errors:
        raise ConfigError("Configuration validation failed:\n  - " + "\n  - ".join(errors))

def load_config():
    load_dotenv()
    cfg = {
        "WEBHOOK_URL": os.getenv("WEBHOOK_URL"),
        "PORT": int(os.getenv("PORT", DEFAULT_PORT)),
        "ACTIVE_UPDATE_INTERVAL": int(os.getenv("ACTIVE_UPDATE_INTERVAL", DEFAULT_UPDATE_INTERVAL)),
        "QB_URL": os.getenv("QB_URL", DEFAULT_QB_URL),
        "QB_USER": os.getenv("QB_USER"),
        "QB_PASS": os.getenv("QB_PASS"),
        "MESSAGE": os.getenv("MESSAGE"),
        "MESSAGE_ID": os.getenv("MESSAGE_ID"),
        "EMBED_SHOW_DOWNLOAD_SPEED": _env_bool("EMBED_SHOW_DOWNLOAD_SPEED", True),
        "EMBED_SHOW_UPLOAD_SPEED": _env_bool("EMBED_SHOW_UPLOAD_SPEED", True),
        "EMBED_SHOW_ETA": _env_bool("EMBED_SHOW_ETA", True),
        "EMBED_SHOW_TIME_ADDED": _env_bool("EMBED_SHOW_TIME_ADDED", True),
        "EMBED_SHOW_TIME_SINCE_STARTED": _env_bool("EMBED_SHOW_TIME_SINCE_STARTED", True),
    }
    validate_config(cfg)
    return cfg

def load_persisted_message_id() -> Optional[str]:
    """Load message ID from persistent storage."""
    if Path(MESSAGE_ID_FILE).exists():
        try:
            with open(MESSAGE_ID_FILE, 'r') as f:
                data = json.load(f)
                return data.get("message_id")
        except Exception as e:
            logger.warning(f"Could not load message ID from file: {e}")
    return None

def save_message_id(message_id: str) -> None:
    """Save message ID to persistent storage."""
    try:
        with open(MESSAGE_ID_FILE, 'w') as f:
            json.dump({"message_id": message_id, "created_at": datetime.datetime.now().isoformat()}, f)
        logger.info(f"Saved message ID to {MESSAGE_ID_FILE}")
    except Exception as e:
        logger.warning(f"Could not save message ID to file: {e}")

def run_status_update(cfg: dict) -> bool:
    global _last_update_time, _last_update_status
    
    try:
        with QBClient(cfg["QB_URL"], cfg.get("QB_USER"), cfg.get("QB_PASS")) as qb:
            if not qb.login():
                raise RuntimeError("qBittorrent login failed")

            active_torrents = qb.get_active_torrents()
            completed_torrents = qb.get_recent_completed_torrents(5)

            embed_options = {
                "show_download_speed": cfg.get("EMBED_SHOW_DOWNLOAD_SPEED", True),
                "show_upload_speed": cfg.get("EMBED_SHOW_UPLOAD_SPEED", True),
                "show_eta": cfg.get("EMBED_SHOW_ETA", True),
                "show_time_added": cfg.get("EMBED_SHOW_TIME_ADDED", True),
                "show_time_since_started": cfg.get("EMBED_SHOW_TIME_SINCE_STARTED", True),
            }
            embed = make_embed(active_torrents, completed_torrents, embed_options)
            
            # Use persisted message ID if not in config
            message_id = cfg.get("MESSAGE_ID") or load_persisted_message_id()
            
            # Send embed and capture returned message ID
            returned_id = send_embed(cfg["WEBHOOK_URL"], embed, cfg.get("MESSAGE"), message_id)
            
            # If this was a new message, save the ID
            if returned_id and not cfg.get("MESSAGE_ID"):
                save_message_id(returned_id)
                logger.info(f"Created new Discord message with ID: {returned_id}")
            
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
            has_active = run_status_update(cfg)
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
        has_active = run_status_update(cfg)
        if has_active:
            ensure_active_monitor_running()
        return jsonify({"status": "updated", "active": has_active, "event": event_type or "unknown"}), 200
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Display version information
    print("=" * 60)
    print(f"qBittorrent Discord Webhook Service")
    print(f"Version: {VERSION}")
    print(f"Build: {BUILD_DATE}")
    print("=" * 60)
    logger.info(f"Starting service - Version {VERSION}, Build {BUILD_DATE}")
    
    try:
        cfg = load_config()
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        print(f"Configuration error: {e}")
        exit(1)
    
    msg = f"Starting webhook server on port {cfg['PORT']}"
    logger.info(msg)
    print(msg)
    
    if cfg.get("WEBHOOK_URL"):
        try:
            has_active = run_status_update(cfg)
            if has_active:
                ensure_active_monitor_running()
            msg = "Startup status check completed."
            logger.info(msg)
            print(msg)
        except Exception as e:
            msg = f"Startup status check failed: {e}"
            logger.error(msg)
            print(msg)
    else:
        msg = "Startup status check skipped: WEBHOOK_URL not set."
        logger.warning(msg)
        print(msg)
    
    app.run(host='0.0.0.0', port=cfg['PORT'])
