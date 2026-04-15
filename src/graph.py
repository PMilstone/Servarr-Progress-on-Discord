from typing import List, Dict
import datetime

def _human_speed(bps: int) -> str:
    if bps >= 1_000_000:
        return f"{bps/1_000_000:.2f} MB/s"
    if bps >= 1_000:
        return f"{bps/1_000:.2f} kB/s"
    return f"{bps} B/s"

def make_text_progress(torrents: List[Dict]) -> str:
    if not torrents:
        return "No active torrents"

    lines = ["**Active Torrent Progress:**\n"]
    for t in torrents:
        name = t["name"]
        progress = t["progress"] * 100
        dls = _human_speed(t.get("dlspeed", 0))
        uls = _human_speed(t.get("ulspeed", 0))

        # Create progress bar with emojis
        bar_length = 20
        filled = int(progress / 100 * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        line = f"**{name}**\n{bar} {progress:.1f}%\n↓ {dls} ↑ {uls}\n\n"
        lines.append(line)

    return "".join(lines)

def make_embed(active_torrents: List[Dict], completed_torrents: List[Dict]) -> Dict[str, object]:
    fields = []
    
    # Active torrents section
    if active_torrents:
        bar_length = 20
        for t in active_torrents[:25]:
            name = t["name"]
            progress = t["progress"] * 100
            dls = _human_speed(t.get("dlspeed", 0))
            uls = _human_speed(t.get("ulspeed", 0))
            filled = int(progress / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            value = f"{bar} {progress:.1f}%\n↓ {dls} ↑ {uls}"
            fields.append({
                "name": name[:256],
                "value": value,
                "inline": False,
            })
    
    # Completed torrents section
    if completed_torrents:
        completed_list = []
        for t in completed_torrents:
            name = t["name"]
            completion_time = datetime.datetime.fromtimestamp(t["completion_on"])
            bar = "█" * 20
            completed_list.append(
                f"✅ {name} - {completion_time.strftime('%Y-%m-%d %H:%M')}\n{bar} 100.0%"
            )
        
        if completed_list:
            fields.append({
                "name": "Recent Completed Downloads",
                "value": "\n".join(completed_list),
                "inline": False,
            })
    
    if not fields:
        return {
            "title": "qBittorrent Status",
            "description": "No torrents found.",
            "color": 3447003,
        }

    return {
        "title": "qBittorrent Status",
        "description": "Active and recent completed torrents tagged tv-arr or movies-arr.",
        "color": 3447003,
        "fields": fields,
    }
