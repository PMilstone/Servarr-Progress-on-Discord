#!/usr/bin/env python3
"""
Test harness for the qBittorrent Discord bot.
Generates sample text progress bars.
"""

from src.graph import make_text_progress

# Mock torrent data
mock_torrents = [
    {"name": "Ubuntu ISO", "progress": 0.85, "dlspeed": 2500000, "ulspeed": 50000, "tags": ""},
    {"name": "Movie File", "progress": 0.45, "dlspeed": 1500000, "ulspeed": 0, "tags": "movies-arr"},
    {"name": "Game Torrent", "progress": 1.0, "dlspeed": 0, "ulspeed": 100000, "tags": ""},
    {"name": "TV Show Episode", "progress": 0.6, "dlspeed": 500000, "ulspeed": 0, "tags": "tv-arr"},
]

# Filter to only show torrents with tv-arr or movies-arr tags
filtered_torrents = [t for t in mock_torrents if "tv-arr" in t.get("tags", "") or "movies-arr" in t.get("tags", "")]

if __name__ == "__main__":
    text = make_text_progress(filtered_torrents)
    print(text)
