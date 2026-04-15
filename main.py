import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from src.qb_client import QBClient
from src.graph import make_embed
from src.discord_webhook import send_embed

app = Flask(__name__)

def load_config():
    load_dotenv()
    return {
        "WEBHOOK_URL": os.getenv("WEBHOOK_URL"),
        "PORT": int(os.getenv("PORT", 5000)),
        "QB_URL": os.getenv("QB_URL", "http://127.0.0.1:8080"),
        "QB_USER": os.getenv("QB_USER"),
        "QB_PASS": os.getenv("QB_PASS"),
        "MESSAGE": os.getenv("MESSAGE"),
        "MESSAGE_ID": os.getenv("MESSAGE_ID"),
    }

def run_status_update(cfg: dict) -> None:
    qb = QBClient(cfg["QB_URL"], cfg.get("QB_USER"), cfg.get("QB_PASS"))
    if not qb.login():
        raise RuntimeError("qBittorrent login failed")

    active_torrents = qb.get_active_torrents()
    completed_torrents = qb.get_recent_completed_torrents(5)

    embed = make_embed(active_torrents, completed_torrents)
    send_embed(cfg["WEBHOOK_URL"], embed, cfg.get("MESSAGE"), cfg.get("MESSAGE_ID"))

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
        run_status_update(cfg)
        return jsonify({"status": "updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    cfg = load_config()
    print(f"Starting webhook server on port {cfg['PORT']}")
    if cfg.get("WEBHOOK_URL"):
        try:
            run_status_update(cfg)
            print("Startup status check completed.")
        except Exception as e:
            print(f"Startup status check failed: {e}")
    else:
        print("Startup status check skipped: WEBHOOK_URL not set.")
    app.run(host='0.0.0.0', port=cfg['PORT'])
