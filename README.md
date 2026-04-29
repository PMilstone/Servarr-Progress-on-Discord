# qBittorrent Discord Webhook

A webhook server that displays qBittorrent download progress in Discord. Shows active downloads with progress bars and recently completed torrents in a single, automatically-updated embed. Integrates seamlessly with Sonarr/Radarr.

## Requirements

- Python 3.10+
- qBittorrent with Web UI enabled
- Discord webhook URL

### Getting a Discord Webhook URL

1. Open Discord and go to your server
2. Go to **Server Settings → Integrations → Webhooks**
3. Click **New Webhook** (or select an existing one)
4. Copy the **Webhook URL**
5. You'll paste this during the setup wizard

## Installation

### Windows
```powershell
.\Servarr-Progress-on-Discord.bat
```

### Linux/Mac
```bash
chmod +x Servarr-Progress-on-Discord.sh
./Servarr-Progress-on-Discord.sh
```

The launcher will automatically:
- Create a virtual environment and install dependencies
- Run the setup wizard if this is your first time
- Start the service if already configured

The setup wizard will guide you through:
- Discord webhook configuration
- qBittorrent connection settings
- Sonarr/Radarr integration (optional)
- Embed customization options

It will send a test message to Discord and offer to start the service immediately after setup.

## Usage

Once configured, the service:
- Listens for webhook events from Sonarr/Radarr
- Monitors qBittorrent for active downloads
- Updates a single Discord message with current progress
- Shows recently completed downloads with relative timestamps

**Test Mode:**
```bash
python main.py --test
```
Runs the service with mock data (no qBittorrent required).

## Sonarr/Radarr Integration

The setup wizard can automatically create webhooks in Sonarr and Radarr. You'll need:
- Your Sonarr/Radarr URL (e.g., `http://127.0.0.1:8989`)
- API Key (found in Settings → General → Security → API Key)

Or manually create webhooks:
1. Go to Settings → Connect in Sonarr/Radarr
2. Add Webhook with URL: `http://your-server-ip:5000/webhook`
3. Enable triggers: On Grab, On Download/Import Complete

## License

Released into the **public domain** under [The Unlicense](LICENSE).

