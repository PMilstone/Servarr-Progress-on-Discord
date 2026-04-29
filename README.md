# qBittorrent Discord Webhook

A production-ready webhook server that displays qBittorrent download progress in Discord. Integrates seamlessly with Sonarr/Radarr to automatically update a Discord embed showing active downloads and recently completed torrents.

## Features

- **Live Progress Updates** - Real-time Discord embed with colorful progress bars for active downloads
- **Smart Title Formatting** - Automatically cleans up torrent names and extracts release years
- **Relative Timestamps** - Completion times and last update show as "2 hours ago" using Discord's native formatting
- **Configurable Display** - Toggle download/upload speeds, ETA, timestamps, and activity duration
- **Category Filtering** - Optionally filter torrents by qBittorrent categories
- **Message Persistence** - Automatically edits the same Discord message instead of spamming
- **Robust Error Handling** - Comprehensive retry logic with exponential backoff
- **Production Ready** - Graceful shutdown, health checks, structured logging, and colorful console output
- **Detailed Error Messages** - Clear troubleshooting guidance with colored terminal output

## Requirements

- Python 3.10+
- qBittorrent with Web UI enabled
- Discord webhook URL
- Sonarr/Radarr (optional, for automatic triggers)

## Installation

### Windows PowerShell
```powershell
# Clone or download the repository
cd path\to\QbitDiscord

# Run launcher (automatically creates venv, installs dependencies, and starts setup or service)
.\Servarr-Progress-on-Discord.bat
```

### Linux/Mac Bash
```bash
# Clone or download the repository
cd path/to/QbitDiscord

# Run launcher (automatically creates venv, installs dependencies, and starts setup or service)
chmod +x Servarr-Progress-on-Discord.sh
./Servarr-Progress-on-Discord.sh
```

**Note:** The launcher automatically:
- Creates a Python virtual environment (`.venv`)
- Installs all required dependencies from `requirements.txt`
- Runs setup wizard if no `.env` file exists
- Starts the service if `.env` file exists

## Configuration

### Option 1: Setup Wizard (Recommended)

Run the unified launcher - it will automatically start the setup wizard if no `.env` file exists:

**Windows:**
```bash
Servarr-Progress-on-Discord.bat
```

**Linux/Mac:**
```bash
chmod +x Servarr-Progress-on-Discord.sh
./Servarr-Progress-on-Discord.sh
```

The wizard will:
- Guide you through all configuration options
- Validate your inputs
- **Send a test message with mock data immediately** to verify webhook works
- Ask you to confirm the message appeared in Discord
- Let you customize the embed display settings
- **Update the test message in real-time** with your customizations
- Automatically capture the message ID for editing
- **Automatically create webhooks in Sonarr/Radarr** if you provide API keys
- Create a ready-to-use `.env` file

The test message sent during setup will be the one edited by the service - no spam!

### Option 2: Manual Configuration

Create a `.env` file with the following settings:

### Required
```ini
WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### Optional
```ini
# Server settings
PORT=5000                          # Webhook server port
ACTIVE_UPDATE_INTERVAL=15          # Update interval in seconds when downloads active
LOG_MAX_SIZE=10485760              # Max log file size in bytes (default 10MB)
                                   # Log rotates when this size is reached

# qBittorrent connection
QB_URL=http://127.0.0.1:8080      # qBittorrent Web UI URL
QB_USER=                           # Leave empty if no authentication
QB_PASS=                           # Leave empty if no authentication

# Sonarr/Radarr integration (optional - for automatic webhook creation)
SONARR_URL=http://127.0.0.1:8989  # Sonarr URL
SONARR_API_KEY=                    # Sonarr API key
RADARR_URL=http://127.0.0.1:7878  # Radarr URL
RADARR_API_KEY=                    # Radarr API key

# Filtering (optional)
QB_CATEGORIES=                     # Comma-separated: tv-arr,movies-arr
                                   # Leave empty to show all torrents

# Discord message options
MESSAGE_ID=                        # Message ID to edit (auto-saved after first run)
MESSAGE=                           # Optional text above the embed

# Embed customization (all default to true)
EMBED_SHOW_DOWNLOAD_SPEED=true
EMBED_SHOW_UPLOAD_SPEED=true
EMBED_SHOW_ETA=true
EMBED_SHOW_TIME_ADDED=true
EMBED_SHOW_TIME_SINCE_STARTED=true
```

### Getting Your Discord Webhook URL
1. Open Discord and navigate to your server
2. Go to Server Settings → Integrations → Webhooks
3. Click "New Webhook" or select an existing one
4. Copy the Webhook URL
5. Paste it into your `.env` file as `WEBHOOK_URL`

## Usage

### Start the Server
```bash
python main.py
```

The server will:
- Start on the configured port (default 5000)
- Perform an initial status check with qBittorrent
- Listen for webhook events from Sonarr/Radarr
- Update Discord automatically when downloads start or complete

### Test Mode

Run the server with mock Linux distro torrents (no qBittorrent required):
```bash
python main.py --test
```

This is useful for:
- Testing Discord webhook integration without qBittorrent
- Verifying configuration and connectivity
- Previewing the embed format and colors
- Development and debugging

The test mode uses mock data with Ubuntu, Debian, Fedora, Arch Linux, and Linux Mint torrents. The Discord embed header will display "TEST - Download Progress" to clearly indicate test mode.

### Command Line Options

```bash
python main.py --help       # Show all available options
python main.py --test       # Run with mock test data
```

### Health Endpoints

The server provides monitoring endpoints:

- `GET /health` - Basic health check (returns 200 OK)
- `GET /status` - Detailed status with last update time and result

Example:
```bash
curl http://localhost:5000/status
```

## Sonarr/Radarr Integration

### Automatic Webhook Setup (Recommended)
The setup wizard can automatically create webhooks in Sonarr and Radarr for you! Just provide:
- Sonarr/Radarr URL (e.g., `http://127.0.0.1:8989` for Sonarr, `http://127.0.0.1:7878` for Radarr)
- API Key (found in Settings → General → Security → API Key)

The wizard will:
- Create a webhook connection named "qBittorrent Discord Status"
- Configure triggers: On Grab, On Import Complete (Sonarr) / On Download (Radarr)
- Set the webhook URL to your server automatically

### Manual Webhook Setup
If you prefer manual setup or automatic creation fails:

1. In Sonarr/Radarr, navigate to **Settings → Connect**
2. Click the **+** button and select **Webhook**
3. Configure the webhook:
   - **Name**: qBittorrent Discord Status
   - **URL**: `http://your-server-ip:5000/webhook`
   - **Method**: POST
   - **On Grab**: ✓ (recommended - triggers when download starts)
   - **On Download**: ✓ (recommended - triggers when download completes)
4. Click **Test** to verify connectivity
5. Save the connection

### Getting Your API Key
1. Open Sonarr or Radarr web interface
2. Go to **Settings → General**
3. Scroll to **Security** section
4. Copy the **API Key**

### Manual Testing
```powershell
# Windows PowerShell
Invoke-WebRequest -Uri http://localhost:5000/webhook -Method POST -ContentType "application/json" -Body '{"eventType":"Grab"}' -UseBasicParsing
```

```bash
# Linux/macOS
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"eventType":"Grab"}'
```

## Troubleshooting

The application provides detailed error messages with actionable troubleshooting steps. Common issues:

### Configuration Errors
If you see a **red error message** about configuration:
- Check that `.env` file exists in the project root
- Verify `WEBHOOK_URL` starts with `https://discord.com/api/webhooks/`
- Ensure `PORT` is between 1-65535
- Verify `QB_URL` starts with `http://` or `https://`

### qBittorrent Connection Issues
If you see **yellow warnings** about qBittorrent:
- Verify qBittorrent is running
- Check that Web UI is enabled: Options → Web UI → Enable
- Confirm `QB_URL` matches your qBittorrent Web UI address
- If authentication is required, set `QB_USER` and `QB_PASS`
- Try "Bypass authentication for localhost" in qBittorrent settings

### Discord Webhook Errors
If Discord messages fail:
- Verify webhook URL is correct and not deleted
- Check internet connectivity
- Visit [Discord Status](https://discordstatus.com) for service issues
- Ensure the webhook hasn't been rate limited

### Unicode/Emoji Display Issues
If you see encoding errors:
- The application automatically uses UTF-8 for log files
- Windows console may not display all emojis (but Discord will)
- Console errors are shown in red/yellow for visibility

### Log Files
The application creates rotating log files:
- Main log: `qbitdiscord.log`
- When the log reaches the configured size (default 10MB), it rotates automatically
- Up to 3 backup files are kept: `qbitdiscord.log.1`, `qbitdiscord.log.2`, `qbitdiscord.log.3`
- Older backups are automatically deleted to save disk space
- Configure max size with `LOG_MAX_SIZE` in `.env` (in bytes)

## Project Structure

```
QbitDiscord/
├── main.py                                # Flask webhook server and orchestration
├── setup.py                               # Interactive setup wizard
├── Servarr-Progress-on-Discord.bat        # Unified launcher (Windows)
├── Servarr-Progress-on-Discord.sh         # Unified launcher (Linux/Mac)
├── requirements.txt                       # Python dependencies
├── .env.example                          # Configuration template
├── .gitignore                            # Git ignore rules
├── LICENSE                               # The Unlicense (public domain)
├── README.md                             # This file
└── src/
    ├── qb_client.py          # qBittorrent API client
    ├── discord_webhook.py    # Discord webhook sender
    └── graph.py              # Embed generation and formatting
```

## Advanced Features

### Category Filtering
By default, the application shows **all torrents** in your qBittorrent client. To filter by categories:

```ini
QB_CATEGORIES=tv-arr,movies-arr,music
```

This will only display torrents whose category contains any of these strings (case-insensitive).

### Message Persistence
The application uses the `MESSAGE_ID` from your `.env` file to edit the same Discord message with each update. If `MESSAGE_ID` is not set, a new message will be created on each update.

To get a message ID:
1. Right-click a message in Discord
2. Select "Copy Message ID" (you may need to enable Developer Mode in Discord settings)
3. Add it to your `.env` file: `MESSAGE_ID=123456789012345678`

The setup wizard can automatically capture this for you during initial configuration.

### Graceful Shutdown
The application handles `CTRL+C` gracefully:
- Stops the background monitor thread
- Closes qBittorrent connections
- Shuts down the Flask server cleanly

## Development

### Testing

**Test with mock data:**
```bash
python main.py --test         # Run server with mock torrents and send to Discord
```

The `--test` flag allows you to test the complete flow (server + Discord webhook + embed generation) without needing qBittorrent installed.

### Version Information
Current version: **1.2.0**  
Build date: **2026-04-29 12:34 PM EST**

## Contributing

Contributions are welcome! This project uses:
- **Flask** for the webhook server
- **requests** for HTTP client operations
- **colorama** for cross-platform colored console output
- **python-dotenv** for environment configuration

## License

This project is released into the **public domain** under [The Unlicense](LICENSE).

You are free to use, modify, distribute, and do whatever you want with this code without any restrictions.
