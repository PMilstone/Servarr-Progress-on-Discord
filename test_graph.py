#!/usr/bin/env python3
"""
Test harness for the qBittorrent Discord webhook service.
Tests the embed generation with mock torrent data.
"""

from src.graph import make_embed
import json

# Mock torrent data matching actual qBittorrent API structure
mock_active_torrents = [
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

mock_completed_torrents = [
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

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Discord Embed Generation")
    print("=" * 60)
    
    # Test with all options enabled
    embed_options = {
        "show_download_speed": True,
        "show_upload_speed": True,
        "show_eta": True,
        "show_time_added": True,
        "show_time_since_started": True,
    }
    
    print("\n1. Testing with active and completed torrents:\n")
    embed = make_embed(mock_active_torrents, mock_completed_torrents, embed_options)
    print(json.dumps(embed, indent=2))
    
    print("\n" + "=" * 60)
    print("2. Testing with no active torrents:\n")
    embed_empty = make_embed([], mock_completed_torrents, embed_options)
    print(json.dumps(embed_empty, indent=2))
    
    print("\n" + "=" * 60)
    print("3. Testing with minimal options:\n")
    minimal_options = {
        "show_download_speed": True,
        "show_upload_speed": False,
        "show_eta": False,
        "show_time_added": False,
        "show_time_since_started": False,
    }
    embed_minimal = make_embed(mock_active_torrents, [], minimal_options)
    print(json.dumps(embed_minimal, indent=2))
    
    print("\n" + "=" * 60)
    print("4. Testing TEST mode (is_test_mode=True):\n")
    embed_test = make_embed(mock_active_torrents, mock_completed_torrents, embed_options, is_test_mode=True)
    print(f"Title: {embed_test['title']}")
    print("(Full embed structure same as test #1, showing title only)")
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")

