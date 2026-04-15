# qBittorrent -> Discord Webhook Status

A webhook server that receives events from Sonarr/Radarr and updates a Discord embed with active qBittorrent torrents and the most recent 5 completed downloads.

## Requirements
- Python 3.10+
- qBittorrent Web UI enabled
- A Discord webhook URL
- Sonarr or Radarr configured to send webhooks

## Quick setup (Windows PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# copy .env.example to .env and edit values
```

## Run the server:
```powershell
python main.py
```

## Configuration
- Copy `.env.example` to `.env` and set:
  - `WEBHOOK_URL`: Your Discord webhook URL
  - `PORT`: Port for the webhook server (default 5000)
  - `ACTIVE_UPDATE_INTERVAL`: Poll interval (seconds) while active downloads exist
  - `QB_URL`, `QB_USER`, `QB_PASS`: qBittorrent settings
  - `MESSAGE_ID`: Optional, message ID to edit instead of sending new
  - `MESSAGE`: Optional, text to include with the embed
  - `EMBED_SHOW_DOWNLOAD_SPEED`: Show download speed in active torrent rows
  - `EMBED_SHOW_UPLOAD_SPEED`: Show upload speed in active torrent rows
  - `EMBED_SHOW_ETA`: Show ETA in active torrent rows
  - `EMBED_SHOW_TIME_ADDED`: Show the torrent added timestamp
  - `EMBED_SHOW_TIME_SINCE_STARTED`: Show active time duration

## How it works
- The server listens for POST requests to `/webhook` from Sonarr/Radarr.
- It triggers on "Grab" (download started) or "Download" (completed) events.
- Checks for active torrents tagged "tv-arr" or "movies-arr".
- Shows the most recent 5 completed downloads with the same tags.
- If `MESSAGE_ID` is set, edits that message; otherwise, sends a new embed.

## Sonarr/Radarr Setup
1. In Sonarr/Radarr, go to Settings → Connect → + Add → Webhook
2. Set URL to: `http://your-server-ip:5000/webhook`
3. Enable "On Grab" and/or "On Download" events
4. Save the connection

## Testing
Send a test POST to the webhook:
```powershell
Invoke-WebRequest -Uri http://127.0.0.1:5000/webhook -Method POST -ContentType "application/json" -Body '{"eventType":"Grab"}' -UseBasicParsing
```
