#!/usr/bin/env python3
"""
Interactive setup script for qBittorrent Discord Webhook Service.
Walks through .env configuration with preview of embed display settings.
"""

import os
import sys
from pathlib import Path
from src.graph import make_embed
from src.discord_webhook import send_embed
import json
import requests
import subprocess

# ANSI color codes for cross-platform colored output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}! {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def prompt_input(prompt_text, default=None, required=True):
    """Prompt for input with optional default value."""
    if default is not None:
        prompt = f"{prompt_text} [{default}]: "
    else:
        prompt = f"{prompt_text}: "
    
    while True:
        value = input(prompt).strip()
        
        if not value and default is not None:
            return default
        
        if not value and not required:
            return ""
        
        if not value and required:
            print_error("This field is required. Please enter a value.")
            continue
        
        return value

def prompt_yes_no(prompt_text, default=True):
    """Prompt for yes/no answer."""
    default_str = "Y/n" if default else "y/N"
    prompt = f"{prompt_text} [{default_str}]: "
    
    while True:
        value = input(prompt).strip().lower()
        
        if not value:
            return default
        
        if value in ('y', 'yes', 'true', '1'):
            return True
        
        if value in ('n', 'no', 'false', '0'):
            return False
        
        print_error("Please enter 'y' or 'n'")

def validate_url(url, url_type="URL"):
    """Basic URL validation."""
    if not url:
        return False
    
    if url_type == "webhook" and not url.startswith("https://discord.com/api/webhooks/"):
        print_warning(f"Warning: Discord webhook URLs typically start with 'https://discord.com/api/webhooks/'")
        if not prompt_yes_no("Continue anyway?", default=False):
            return False
    
    if url_type == "qbittorrent" and not (url.startswith("http://") or url.startswith("https://")):
        print_error("qBittorrent URL must start with http:// or https://")
        return False
    
    return True

def create_arr_webhook(app_name, base_url, api_key, webhook_server_url):
    """
    Create a webhook in Sonarr or Radarr using their API.
    
    Args:
        app_name: "Sonarr" or "Radarr"
        base_url: Base URL of the Sonarr/Radarr instance
        api_key: API key for authentication
        webhook_server_url: URL of our webhook server (e.g., http://localhost:5000/webhook)
    
    Returns:
        True if successful, False otherwise
    """
    if not base_url or not api_key:
        return False
    
    # Construct API endpoint
    api_url = f"{base_url.rstrip('/')}/api/v3/notification"
    
    # Webhook configuration
    # Sonarr uses "onImportComplete" and "onManualInteractionRequired"
    # Radarr uses "onDownload" and "onManualInteractionRequired"
    is_sonarr = app_name.lower() == "sonarr"
    
    webhook_config = {
        "name": "qBittorrent Discord Status",
        "implementation": "Webhook",
        "configContract": "WebhookSettings",
        "fields": [
            {"name": "url", "value": webhook_server_url},
            {"name": "method", "value": 1}  # 1 = POST
        ],
        "tags": [],
        "onGrab": True,
        "onHealthIssue": False,
        "onApplicationUpdate": False,
        "includeHealthWarnings": False
    }
    
    # Add app-specific triggers
    if is_sonarr:
        webhook_config["onImportComplete"] = True
        webhook_config["onSeriesDelete"] = False
        webhook_config["onEpisodeFileDelete"] = False
    else:  # Radarr
        webhook_config["onDownload"] = True
        webhook_config["onMovieDelete"] = False
        webhook_config["onMovieFileDelete"] = False
    
    try:
        response = requests.post(
            api_url,
            headers={
                "X-Api-Key": api_key,
                "Content-Type": "application/json"
            },
            json=webhook_config,
            timeout=10
        )
        
        if response.status_code == 201:
            return True
        elif response.status_code == 400:
            # Check if webhook already exists
            error_msg = response.text.lower()
            if "already exists" in error_msg or "duplicate" in error_msg:
                print_warning(f"{app_name} webhook may already exist")
                return True
            return False
        else:
            print_error(f"{app_name} API returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to connect to {app_name}: {str(e)}")
        return False

def get_embed_settings():
    """Prompt for all embed display settings."""
    print("\n" + Colors.BOLD + "Embed Display Settings" + Colors.END)
    print("Configure what information to show in the Discord embed:\n")
    
    settings = {
        "EMBED_SHOW_DOWNLOAD_SPEED": prompt_yes_no("Show download speed?", default=True),
        "EMBED_SHOW_UPLOAD_SPEED": prompt_yes_no("Show upload speed?", default=True),
        "EMBED_SHOW_ETA": prompt_yes_no("Show estimated time remaining (ETA)?", default=True),
        "EMBED_SHOW_TIME_ADDED": prompt_yes_no("Show when torrent was added?", default=True),
        "EMBED_SHOW_TIME_SINCE_STARTED": prompt_yes_no("Show how long torrent has been active?", default=True),
    }
    
    return settings

def show_embed_preview(embed_settings):
    """Generate and display a preview of the embed with current settings."""
    # Mock test data
    mock_active = [{
        "name": "Ubuntu.22.04.3.LTS.Desktop.amd64.iso",
        "progress": 0.65,
        "dlspeed": 5500000,
        "ulspeed": 125000,
        "eta": 450,
        "added_on": 1714000000,
        "time_active": 300,
        "size": 3500000000,
        "state": "downloading"
    }]
    
    mock_completed = [{
        "name": "Fedora.Workstation.39.x86_64.iso",
        "completion_on": 1714350000,
        "size": 2100000000
    }]
    
    # Convert settings to options format
    options = {
        "show_download_speed": embed_settings["EMBED_SHOW_DOWNLOAD_SPEED"],
        "show_upload_speed": embed_settings["EMBED_SHOW_UPLOAD_SPEED"],
        "show_eta": embed_settings["EMBED_SHOW_ETA"],
        "show_time_added": embed_settings["EMBED_SHOW_TIME_ADDED"],
        "show_time_since_started": embed_settings["EMBED_SHOW_TIME_SINCE_STARTED"],
    }
    
    embed = make_embed(mock_active, mock_completed, options)
    
    print("\n" + Colors.BOLD + Colors.GREEN + "=" * 70 + Colors.END)
    print(Colors.BOLD + Colors.GREEN + "EMBED PREVIEW" + Colors.END)
    print(Colors.BOLD + Colors.GREEN + "=" * 70 + Colors.END)
    
    print(f"\n{Colors.BOLD}Title:{Colors.END} {embed['title']}")
    print(f"{Colors.BOLD}Color:{Colors.END} #{embed['color']:06x}\n")
    
    for field in embed['fields']:
        print(f"{Colors.BOLD}{field['name']}{Colors.END}")
        # Clean up Discord timestamp format and emoji for display
        # Show that these will appear as relative times in Discord (e.g., "2 hours ago")
        value = field['value'].replace('<t:', '[').replace(':R>', ' - relative time]')
        print(f"  {value}")
        print()
    
    print(Colors.BOLD + Colors.GREEN + "=" * 70 + Colors.END + "\n")

def send_test_message_to_discord(webhook_url, embed_settings, message_content=None, existing_message_id=None):
    """
    Send a test message to Discord and return the message ID.
    
    Args:
        webhook_url: Discord webhook URL
        embed_settings: Dictionary of embed display settings
        message_content: Optional message content to send with embed
        existing_message_id: If provided, will edit this message instead of creating new
    
    Returns:
        Message ID if successful, None if failed
    """
    if existing_message_id:
        print("\n" + Colors.BOLD + "Updating test message in Discord..." + Colors.END)
    else:
        print("\n" + Colors.BOLD + "Sending test message to Discord..." + Colors.END)
    
    # Create mock test data
    mock_active = [{
        "name": "Ubuntu.22.04.3.LTS.Desktop.amd64.iso",
        "progress": 0.65,
        "dlspeed": 5500000,
        "ulspeed": 125000,
        "eta": 450,
        "added_on": 1714000000,
        "time_active": 300,
        "size": 3500000000,
        "state": "downloading"
    }]
    
    mock_completed = [{
        "name": "Fedora.Workstation.39.x86_64.iso",
        "completion_on": 1714350000,
        "size": 2100000000
    }]
    
    # Convert settings to options format
    options = {
        "show_download_speed": embed_settings["EMBED_SHOW_DOWNLOAD_SPEED"],
        "show_upload_speed": embed_settings["EMBED_SHOW_UPLOAD_SPEED"],
        "show_eta": embed_settings["EMBED_SHOW_ETA"],
        "show_time_added": embed_settings["EMBED_SHOW_TIME_ADDED"],
        "show_time_since_started": embed_settings["EMBED_SHOW_TIME_SINCE_STARTED"],
    }
    
    # Generate embed with test mode indicator
    embed = make_embed(mock_active, mock_completed, options, is_test_mode=True)
    
    try:
        # Send to Discord and capture message ID
        message_id = send_embed(webhook_url, embed, message_content, message_id=existing_message_id)
        
        if message_id:
            if existing_message_id:
                print_success(f"Test message updated successfully!")
            else:
                print_success(f"Test message sent successfully!")
            print(f"\n{Colors.BOLD}Message ID:{Colors.END} {message_id}")
            print(f"{Colors.BOLD}Check your Discord channel to see the live embed!{Colors.END}\n")
            return message_id
        else:
            print_error("Failed to get message ID from Discord response")
            return None
            
    except Exception as e:
        print_error(f"Failed to send test message: {e}")
        return None

def main():
    print_header("qBittorrent Discord Webhook Service - Setup Wizard")
    
    print("This wizard will help you create a .env configuration file.")
    print("Press Ctrl+C at any time to cancel.\n")
    
    # Check if .env already exists
    env_path = Path(".env")
    if env_path.exists():
        print_warning(".env file already exists!")
        if not prompt_yes_no("Do you want to overwrite it?", default=False):
            print("\nSetup cancelled.")
            return
        print()
    
    config = {}
    
    # Discord Webhook URL (required)
    print_header("Step 1: Discord Webhook")
    print("To get a webhook URL:")
    print("  1. Open Discord and go to Server Settings → Integrations")
    print("  2. Click 'Webhooks' → 'New Webhook'")
    print("  3. Copy the Webhook URL\n")
    
    while True:
        webhook_url = prompt_input("Enter Discord Webhook URL", required=True)
        if validate_url(webhook_url, "webhook"):
            config["WEBHOOK_URL"] = webhook_url
            break
    
    # Server Port
    print_header("Step 2: Server Configuration")
    config["PORT"] = prompt_input("Server port", default="5000", required=False)
    config["ACTIVE_UPDATE_INTERVAL"] = prompt_input("Update interval in seconds (while downloads active)", default="15", required=False)
    log_mb = prompt_input("Maximum log file size in MB", default="10", required=False)
    # Convert MB to bytes for storage in .env
    config["LOG_MAX_SIZE"] = str(int(float(log_mb) * 1048576))
    
    # qBittorrent Configuration
    print_header("Step 3: qBittorrent Configuration")
    print("Enter your qBittorrent Web UI URL (e.g., http://127.0.0.1:8080)\n")
    
    while True:
        qb_url = prompt_input("qBittorrent Web UI URL", default="http://127.0.0.1:8080", required=True)
        if validate_url(qb_url, "qbittorrent"):
            config["QB_URL"] = qb_url
            break
    
    print("\nIf qBittorrent Web UI requires authentication, enter credentials.")
    print("Leave blank if authentication is not required.\n")
    config["QB_USER"] = prompt_input("qBittorrent username", required=False)
    config["QB_PASS"] = prompt_input("qBittorrent password", required=False)
    
    # Sonarr/Radarr Configuration (optional)
    print_header("Step 3.5: Sonarr/Radarr Configuration (Optional)")
    print("Configure Sonarr and/or Radarr to enable automatic webhook creation.")
    print("Leave blank to skip and manually configure webhooks later.\n")
    
    print("Sonarr Configuration:")
    config["SONARR_URL"] = prompt_input("Sonarr URL", default="http://127.0.0.1:8989", required=False)
    if config["SONARR_URL"]:
        config["SONARR_API_KEY"] = prompt_input("Sonarr API Key", required=False)
    else:
        config["SONARR_API_KEY"] = ""
    
    print("\nRadarr Configuration:")
    config["RADARR_URL"] = prompt_input("Radarr URL", default="http://127.0.0.1:7878", required=False)
    if config["RADARR_URL"]:
        config["RADARR_API_KEY"] = prompt_input("Radarr API Key", required=False)
    else:
        config["RADARR_API_KEY"] = ""
    
    # Send initial test message with default settings to verify webhook
    print_header("Step 4: Discord Webhook Test")
    
    print("Let's verify your webhook works by sending a test message!")
    print("This will send a test embed with mock torrent data to your Discord channel.\n")
    
    # Use default embed settings for initial test
    default_embed_settings = {
        "EMBED_SHOW_DOWNLOAD_SPEED": True,
        "EMBED_SHOW_UPLOAD_SPEED": True,
        "EMBED_SHOW_ETA": True,
        "EMBED_SHOW_TIME_ADDED": True,
        "EMBED_SHOW_TIME_SINCE_STARTED": True,
    }
    
    if prompt_yes_no("Send test message to Discord now?", default=True):
        print("\n" + Colors.BOLD + "Sending test message with mock data..." + Colors.END)
        
        message_id = send_test_message_to_discord(
            config['WEBHOOK_URL'],
            default_embed_settings,
            message_content=None
        )
        
        if not message_id:
            print_error("\nFailed to send test message to Discord.")
            print("Possible issues:")
            print("  • Invalid webhook URL")
            print("  • Webhook was deleted")
            print("  • Network connectivity problems")
            print("\nSetup cannot continue without a valid webhook.")
            return
        
        # Success - ask user to verify
        print("\n" + Colors.BOLD + Colors.GREEN + "=" * 70 + Colors.END)
        print(Colors.BOLD + Colors.GREEN + "✓ TEST MESSAGE SENT!" + Colors.END)
        print(Colors.BOLD + Colors.GREEN + "=" * 70 + Colors.END)
        print(f"\n{Colors.BOLD}Check your Discord channel now!{Colors.END}")
        print(f"A test message should appear with mock download progress.\n")
        print(f"Message ID: {Colors.GREEN}{message_id}{Colors.END}\n")
        
        if not prompt_yes_no("Did you see the test message in Discord?", default=True):
            print_error("\nTest message not visible in Discord.")
            print("Please check:")
            print("  • You're looking at the correct Discord channel")
            print("  • The webhook URL is correct")
            print("  • You have permission to view the channel")
            if not prompt_yes_no("\nContinue setup anyway?", default=False):
                print("\nSetup cancelled.")
                return
        
        print_success("Great! Webhook is working correctly.\n")
    else:
        print_warning("Skipping test message. Configuration will continue without validation.\n")
        message_id = None
    
    # Optional Settings
    print_header("Step 5: Optional Settings")
    config["MESSAGE"] = prompt_input("Optional message to send with embeds", default="Download status update", required=False)
    
    print("\nCategory Filter (optional):")
    print("  Leave blank to show ALL torrents.")
    print("  Or enter comma-separated category substrings to filter (e.g., 'tv-arr,movies-arr')\n")
    config["QB_CATEGORIES"] = prompt_input("Category filter", required=False)
    
    # Embed Display Settings with Live Discord Preview
    print_header("Step 6: Embed Display Customization")
    
    if message_id:
        print("Now let's customize what information to show in the embed.")
        print("After you configure the settings, we'll update the test message in Discord")
        print("so you can see exactly how it will look.\n")
    else:
        print("Configure what information to show in the Discord embed:\n")
    
    config["MESSAGE_ID"] = message_id or ""  # Use captured message ID or empty
    
    while True:
        embed_settings = get_embed_settings()
        config.update(embed_settings)
        
        if message_id:
            # Update the existing test message with new settings
            updated_id = send_test_message_to_discord(
                config['WEBHOOK_URL'],
                embed_settings,
                config.get('MESSAGE'),
                existing_message_id=message_id
            )
            
            if not updated_id:
                print_warning("Could not update test message, but settings are saved.")
            else:
                print("\n" + Colors.BOLD + Colors.GREEN + "=" * 70 + Colors.END)
                print(Colors.BOLD + Colors.GREEN + "CHECK YOUR DISCORD CHANNEL NOW!" + Colors.END)
                print(Colors.BOLD + Colors.GREEN + "=" * 70 + Colors.END)
                print(f"\n{Colors.BOLD}The test message has been updated with your settings.{Colors.END}\n")
            
            if prompt_yes_no("Does the message look good in Discord?", default=True):
                print_success("Perfect! Settings confirmed.")
                break
            
            print("\nLet's adjust the settings and try again...\n")
        else:
            # No test message sent, just confirm settings
            show_embed_preview(embed_settings)
            
            if prompt_yes_no("Do these settings look good?", default=True):
                break
            
            print("\nLet's adjust the settings...\n")
    
    # Message ID confirmation
    print_header("Step 7: Configuration Summary")
    
    print(f"{Colors.BOLD}Configuration Complete!{Colors.END}\n")
    print(f"• Discord webhook configured")
    print(f"• qBittorrent connection configured")
    print(f"• Embed settings configured")
    
    if config.get('MESSAGE_ID'):
        print(f"• Message ID captured: {Colors.GREEN}{config['MESSAGE_ID']}{Colors.END}")
        print(f"\nThe service will edit the test message you saw in Discord.")
        print(f"No new messages will be created - it will update that same message!\n")
    else:
        print(f"• Message ID: {Colors.YELLOW}Not set{Colors.END}")
        print(f"\nThe service will create a new message on first run.\n")
    
    # Write .env file
    print_header("Writing Configuration")
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write("# qBittorrent Discord Webhook Configuration\n")
        f.write("# Generated by setup wizard\n\n")
        
        f.write("# Discord webhook URL (required)\n")
        f.write(f"WEBHOOK_URL={config['WEBHOOK_URL']}\n\n")
        
        f.write("# Port for the webhook server (default 5000)\n")
        f.write(f"PORT={config['PORT']}\n\n")
        
        f.write("# Poll interval in seconds while active downloads exist\n")
        f.write(f"ACTIVE_UPDATE_INTERVAL={config['ACTIVE_UPDATE_INTERVAL']}\n\n")
        
        f.write("# Maximum log file size in bytes before rotation\n")
        f.write(f"LOG_MAX_SIZE={config['LOG_MAX_SIZE']}\n\n")
        
        f.write("# qBittorrent web UI base URL\n")
        f.write(f"QB_URL={config['QB_URL']}\n\n")
        
        f.write("# qBittorrent credentials (leave blank if not required)\n")
        f.write(f"QB_USER={config['QB_USER']}\n")
        f.write(f"QB_PASS={config['QB_PASS']}\n\n")
        
        if config['SONARR_URL']:
            f.write("# Sonarr configuration (optional)\n")
            f.write(f"SONARR_URL={config['SONARR_URL']}\n")
            f.write(f"SONARR_API_KEY={config['SONARR_API_KEY']}\n\n")
        
        if config['RADARR_URL']:
            f.write("# Radarr configuration (optional)\n")
            f.write(f"RADARR_URL={config['RADARR_URL']}\n")
            f.write(f"RADARR_API_KEY={config['RADARR_API_KEY']}\n\n")
        
        if config['MESSAGE']:
            f.write("# Optional message content to send with each embed\n")
            f.write(f"MESSAGE={config['MESSAGE']}\n\n")
        
        if config.get('MESSAGE_ID'):
            f.write("# Discord message ID (captured during setup - this message will be edited)\n")
            f.write(f"MESSAGE_ID={config['MESSAGE_ID']}\n\n")
        
        f.write("# Embed display toggles (true/false)\n")
        f.write(f"EMBED_SHOW_DOWNLOAD_SPEED={str(config['EMBED_SHOW_DOWNLOAD_SPEED']).lower()}\n")
        f.write(f"EMBED_SHOW_UPLOAD_SPEED={str(config['EMBED_SHOW_UPLOAD_SPEED']).lower()}\n")
        f.write(f"EMBED_SHOW_ETA={str(config['EMBED_SHOW_ETA']).lower()}\n")
        f.write(f"EMBED_SHOW_TIME_ADDED={str(config['EMBED_SHOW_TIME_ADDED']).lower()}\n")
        f.write(f"EMBED_SHOW_TIME_SINCE_STARTED={str(config['EMBED_SHOW_TIME_SINCE_STARTED']).lower()}\n\n")
        
        if config['QB_CATEGORIES']:
            f.write("# qBittorrent category filter (comma-separated)\n")
            f.write(f"QB_CATEGORIES={config['QB_CATEGORIES']}\n")
    
    print_success(f"Configuration saved to {env_path.absolute()}")
    
    # Automatically create webhooks in Sonarr/Radarr if configured
    if config.get('SONARR_URL') and config.get('SONARR_API_KEY'):
        print_header("Creating Sonarr Webhook")
        webhook_url = f"http://127.0.0.1:{config['PORT']}/webhook"
        print(f"Attempting to create webhook in Sonarr: {webhook_url}\n")
        
        if create_arr_webhook("Sonarr", config['SONARR_URL'], config['SONARR_API_KEY'], webhook_url):
            print_success("Sonarr webhook created successfully!")
            print(f"  Triggers: On Grab, On Import Complete\n")
        else:
            print_warning("Could not automatically create Sonarr webhook.")
            print(f"  You can manually create it in Sonarr:")
            print(f"  Settings → Connect → Add Webhook")
            print(f"  URL: {webhook_url}\n")
    
    if config.get('RADARR_URL') and config.get('RADARR_API_KEY'):
        print_header("Creating Radarr Webhook")
        webhook_url = f"http://127.0.0.1:{config['PORT']}/webhook"
        print(f"Attempting to create webhook in Radarr: {webhook_url}\n")
        
        if create_arr_webhook("Radarr", config['RADARR_URL'], config['RADARR_API_KEY'], webhook_url):
            print_success("Radarr webhook created successfully!")
            print(f"  Triggers: On Grab, On Download\n")
        else:
            print_warning("Could not automatically create Radarr webhook.")
            print(f"  You can manually create it in Radarr:")
            print(f"  Settings → Connect → Add Webhook")
            print(f"  URL: {webhook_url}\n")
    
    print_header("Setup Complete!")
    
    if config.get('MESSAGE_ID'):
        print_success("A test message was created in your Discord channel.")
        print(f"The service will automatically edit that message with live updates.\n")
    
    print(f"{Colors.BOLD}Configuration is complete!{Colors.END}\n")
    
    # Ask if user wants to start the service now
    if prompt_yes_no("Would you like to start the service now?", default=True):
        print_header("Starting Service")
        print(f"Launching {Colors.BOLD}main.py{Colors.END}...\n")
        
        try:
            # Get the Python executable from the current environment
            python_exe = sys.executable
            script_path = Path(__file__).parent / "main.py"
            
            # Launch main.py in the same process
            print(f"{Colors.GREEN}{'=' * 70}{Colors.END}")
            print(f"{Colors.GREEN}Service is starting...{Colors.END}")
            print(f"{Colors.GREEN}{'=' * 70}{Colors.END}\n")
            
            # Execute main.py
            os.execv(python_exe, [python_exe, str(script_path)])
            
        except Exception as e:
            print_error(f"Failed to start service: {e}")
            print("\nYou can manually start the service with:")
            print(f"  {Colors.BOLD}python main.py{Colors.END}\n")
            sys.exit(1)
    else:
        print("\nYou can start the service later with:")
        print(f"  {Colors.BOLD}python main.py{Colors.END}\n")
        print("Or test with mock data:")
        print(f"  {Colors.BOLD}python main.py --test{Colors.END}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nSetup failed: {e}")
        sys.exit(1)
