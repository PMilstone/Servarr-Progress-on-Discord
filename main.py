import os
import threading
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from src.qb_client import QBClient
from src.graph import make_embed
from src.discord_webhook import send_embed

app = Flask(__name__)
_active_monitor_thread = None
_active_monitor_lock = threading.Lock()

def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def load_config():
    load_dotenv()
    return {
        "WEBHOOK_URL": os.getenv("WEBHOOK_URL"),
        "PORT": int(os.getenv("PORT", 5000)),
        "ACTIVE_UPDATE_INTERVAL": int(os.getenv("ACTIVE_UPDATE_INTERVAL", 15)),
        "QB_URL": os.getenv("QB_URL", "http://127.0.0.1:8080"),
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

def run_status_update(cfg: dict) -> bool:
    qb = QBClient(cfg["QB_URL"], cfg.get("QB_USER"), cfg.get("QB_PASS"))
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
    send_embed(cfg["WEBHOOK_URL"], embed, cfg.get("MESSAGE"), cfg.get("MESSAGE_ID"))
    return len(active_torrents) > 0

def _monitor_active_downloads() -> None:
    while True:
        cfg = load_config()
        if not cfg.get("WEBHOOK_URL"):
            break

        try:
            has_active = run_status_update(cfg)
        except Exception as e:
            print(f"Active download monitor error: {e}")
            break

        if not has_active:
            break

        interval = max(1, int(cfg.get("ACTIVE_UPDATE_INTERVAL", 15)))
        time.sleep(interval)

def ensure_active_monitor_running() -> None:
    global _active_monitor_thread
    with _active_monitor_lock:
        if _active_monitor_thread and _active_monitor_thread.is_alive():
            return
        _active_monitor_thread = threading.Thread(target=_monitor_active_downloads, daemon=True)
        _active_monitor_thread.start()

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

    event_type = data.get("eventType")
    # Trigger on Grab (download started), Download (completed), or Import (file imported)
    if event_type not in ["Grab", "Download", "Import"]:
        return jsonify({"status": "ignored", "event": event_type}), 200

    try:
        has_active = run_status_update(cfg)
        if has_active:
            ensure_active_monitor_running()
        return jsonify({"status": "updated", "active": has_active}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    cfg = load_config()
    print(f"Starting webhook server on port {cfg['PORT']}")
    if cfg.get("WEBHOOK_URL"):
        try:
            has_active = run_status_update(cfg)
            if has_active:
                ensure_active_monitor_running()
            print("Startup status check completed.")
        except Exception as e:
            print(f"Startup status check failed: {e}")
    else:
        print("Startup status check skipped: WEBHOOK_URL not set.")
    app.run(host='0.0.0.0', port=cfg['PORT'])
