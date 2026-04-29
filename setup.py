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

def send_test_message_to_discord(webhook_url, embed_settings, message_content=None):
    """
    Send a test message to Discord and return the message ID.
    
    Returns:
        Message ID if successful, None if failed
    """
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
        message_id = send_embed(webhook_url, embed, message_content, message_id=None)
        
        if message_id:
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
    config["LOG_MAX_SIZE"] = prompt_input("Maximum log file size in bytes", default="10485760", required=False)
    
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
    
    # Optional Settings
    print_header("Step 4: Optional Settings")
    config["MESSAGE"] = prompt_input("Optional message to send with embeds", default="Download status update", required=False)
    
    print("\nCategory Filter (optional):")
    print("  Leave blank to show ALL torrents.")
    print("  Or enter comma-separated category substrings to filter (e.g., 'tv-arr,movies-arr')\n")
    config["QB_CATEGORIES"] = prompt_input("Category filter", required=False)
    
    # Embed Display Settings with Preview Loop
    print_header("Step 5: Embed Display Settings")
    
    while True:
        embed_settings = get_embed_settings()
        config.update(embed_settings)
        
        show_embed_preview(embed_settings)
        
        if prompt_yes_no("Does this embed preview look good?", default=True):
            break
        
        print("\nLet's adjust the embed settings...\n")
    
    # Send test message to Discord and capture message ID
    print_header("Step 6: Discord Test Message")
    
    print("The setup wizard can send a test message to your Discord channel.")
    print("This will:")
    print("  • Validate your webhook URL works")
    print("  • Show you the actual live Discord embed")
    print("  • Automatically capture the message ID for editing")
    print(f"  • The service will edit this message instead of creating new ones\n")
    
    config["MESSAGE_ID"] = ""  # Default to empty
    
    if prompt_yes_no("Send a test message to Discord now?", default=True):
        message_id = send_test_message_to_discord(
            config['WEBHOOK_URL'],
            embed_settings,
            config.get('MESSAGE')
        )
        
        if message_id:
            print_success("Message ID captured! The service will edit this message on future updates.")
            config["MESSAGE_ID"] = message_id
        else:
            print_warning("Could not capture message ID. The service will create a new message on first run.")
            if prompt_yes_no("Continue anyway?", default=True):
                pass
            else:
                print("\nSetup cancelled.")
                return
    else:
        print("\nSkipping test message. The service will create a new message on first run.")
    
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
        
        f.write("# Maximum log file size in bytes before rotation (default 10485760 = 10MB)\n")
        f.write(f"LOG_MAX_SIZE={config['LOG_MAX_SIZE']}\n\n")
        
        f.write("# qBittorrent web UI base URL\n")
        f.write(f"QB_URL={config['QB_URL']}\n\n")
        
        f.write("# qBittorrent credentials (leave blank if not required)\n")
        f.write(f"QB_USER={config['QB_USER']}\n")
        f.write(f"QB_PASS={config['QB_PASS']}\n\n")
        
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
    
    print_header("Setup Complete!")
    
    if config.get('MESSAGE_ID'):
        print_success("A test message was created in your Discord channel.")
        print(f"The service will automatically edit that message with live updates.\n")
    
    print("You can now start the service with:")
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
