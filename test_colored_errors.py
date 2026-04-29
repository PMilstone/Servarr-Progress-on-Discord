#!/usr/bin/env python3
"""
Test harness to demonstrate colored error messages.
Run this to see error messages in red, warnings in yellow, and success in green.
"""

from colorama import init as colorama_init, Fore, Style

# Initialize colorama
colorama_init(autoreset=True)

def print_error(msg: str) -> None:
    """Print error message in red."""
    print(f"{Fore.RED}{msg}{Style.RESET_ALL}")

def print_warning(msg: str) -> None:
    """Print warning message in yellow."""
    print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")

def print_success(msg: str) -> None:
    """Print success message in green."""
    print(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Testing Colored Console Output")
    print("=" * 70 + "\n")
    
    # Test error (red)
    print_error("CRITICAL ERROR: Configuration validation failed")
    print_error("    → WEBHOOK_URL is required but not set.")
    print_error("    → Create a .env file in the project root")
    print_error("    → Add: WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL")
    
    print("\n" + "-" * 70 + "\n")
    
    # Test warning (yellow)
    print_warning("WARNING: Could not connect to qBittorrent at startup")
    print_warning("  → Check if qBittorrent is running")
    print_warning("  → Verify QB_URL setting: http://127.0.0.1:8080")
    print_warning("  → Check username/password if required")
    
    print("\n" + "-" * 70 + "\n")
    
    # Test success (green)
    print_success("Startup status check completed successfully.")
    print_success("Discord webhook connection established")
    print_success("qBittorrent client connected successfully")
    
    print("\n" + "=" * 70)
    print("Color test completed!")
    print("=" * 70 + "\n")
