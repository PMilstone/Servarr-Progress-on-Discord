from typing import List, Dict
import datetime
import re

# Constants
PROGRESS_BAR_LENGTH = 12
MAX_ACTIVE_TORRENTS_DISPLAY = 25
MAX_TITLE_LENGTH = 256
ETA_MIN_PROGRESS_THRESHOLD = 0.10  # 10% - Hold ETA display until this progress
ETA_MIN_TIME_ACTIVE = 60  # seconds - Hold ETA display until this much time has passed

def _format_datetime_12h(dt: datetime.datetime) -> str:
    hour = dt.hour % 12 or 12
    return f"{dt.strftime('%Y-%m-%d')} {hour}:{dt.strftime('%M %p')}"

def _human_speed(bps: int) -> str:
    if bps >= 1_000_000:
        return f"{bps/1_000_000:.2f} MB/s"
    if bps >= 1_000:
        return f"{bps/1_000:.2f} kB/s"
    return f"{bps} B/s"

def _human_duration(seconds: int) -> str:
    if seconds is None or seconds < 0:
        return "Unknown"
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

def _human_timestamp(ts: int) -> str:
    if not ts or ts <= 0:
        return "Unknown"
    return _format_datetime_12h(datetime.datetime.fromtimestamp(ts))

def _extract_year(text: str) -> str:
    # Capture release years but avoid years that are part of full dates like 2026-04-15.
    match = re.search(r"\b(19\d{2}|20\d{2})(?!-\d{2}-\d{2})\b", text)
    return match.group(1) if match else ""

def _format_title(raw_name: str) -> str:
    # Remove leading uploader/group tags like [YTS], [RARBG], etc.
    raw_name = re.sub(r"^\s*(\[[^\]]+\]\s*)+", "", raw_name)
    # Preserve any valid year before dropping trailing bracket metadata.
    preserved_year = _extract_year(raw_name)
    # Remove trailing bracket metadata blocks, including dangling/incomplete brackets.
    raw_name = re.sub(r"\s*(\[[^\]]*\]\s*)+$", "", raw_name)
    raw_name = re.sub(r"\s*\[[^\]]*$", "", raw_name)

    # Remove extension-like suffixes and normalize separators.
    name = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", raw_name)
    name = name.replace("_", " ").replace(".", " ")
    name = re.sub(r"\s+", " ", name).strip()

    # Find year in a sensible range.
    year = _extract_year(name) or preserved_year

    # Trim common release metadata after the title.
    cut_tokens = [
        " 2160p", " 1080p", " 720p", " x264", " x265", " h264", " h265",
        " bluray", " web-dl", " webrip", " dvdrip", " remux", " proper", " repack",
        " yify", " rarbg", " dts", " aac", " hdr", " hevc", " atmos", " season ", " s01",
    ]
    lower_name = name.lower()
    cut_positions = []
    for token in cut_tokens:
        pos = lower_name.find(token)
        if pos != -1:
            cut_positions.append(pos)
    year_match = re.search(rf"\b{re.escape(year)}\b", name) if year else None
    if year_match:
        cut_positions.append(year_match.start())

    if cut_positions:
        name = name[:min(cut_positions)].strip(" -_.")

    if not name:
        name = raw_name.strip()

    if year:
        return f"{name} ({year})"
    return name

def _format_eta(progress: float, time_active: int, eta_seconds: int) -> str:
    # qBittorrent ETA can be noisy at startup. Hold until either threshold is reached.
    if progress < ETA_MIN_PROGRESS_THRESHOLD and time_active < ETA_MIN_TIME_ACTIVE:
        return "Calculating..."
    return _human_duration(eta_seconds)

def _rainbow_progress_bar(progress_ratio: float, length: int = PROGRESS_BAR_LENGTH) -> str:
    colors = ["🟦", "🟦", "🟩", "🟩", "🟨", "🟨", "🟧", "🟧", "🟥", "🟥", "🟪", "🟪"]
    safe_ratio = max(0.0, min(1.0, progress_ratio))
    filled = int(safe_ratio * length)
    bar = "".join(colors[i % len(colors)] for i in range(filled))
    return bar + ("⬜" * (length - filled))

def make_embed(active_torrents: List[Dict], completed_torrents: List[Dict], options: Dict[str, bool] | None = None) -> Dict[str, object]:
    options = options or {}
    show_download_speed = options.get("show_download_speed", True)
    show_upload_speed = options.get("show_upload_speed", True)
    show_eta = options.get("show_eta", True)
    show_time_added = options.get("show_time_added", True)
    show_time_since_started = options.get("show_time_since_started", True)

    fields = []
    
    # Active torrents section
    if active_torrents:
        for t in active_torrents[:MAX_ACTIVE_TORRENTS_DISPLAY]:
            name = _format_title(t["name"])
            progress_ratio = t["progress"]
            progress = progress_ratio * 100
            bar = _rainbow_progress_bar(progress_ratio, PROGRESS_BAR_LENGTH)
            details = []
            if show_download_speed:
                details.append(f"↓ {_human_speed(t.get('dlspeed', 0))}")
            if show_upload_speed:
                details.append(f"↑ {_human_speed(t.get('ulspeed', 0))}")
            if show_eta:
                details.append(
                    f"ETA: {_format_eta(t.get('progress', 0.0), t.get('time_active', 0), t.get('eta', -1))}"
                )
            if show_time_added:
                details.append(f"Added {_human_timestamp(t.get('added_on', 0))}")
            if show_time_since_started:
                details.append(f"Active {_human_duration(t.get('time_active', 0))}")

            value = f"{bar} {progress:.1f}%"
            if details:
                value = value + "\n" + " | ".join(details)
            fields.append({
                "name": name[:MAX_TITLE_LENGTH],
                "value": value,
                "inline": False,
            })
    else:
        fields.append({
            "name": "Active Downloads",
            "value": "_No active downloads._",
            "inline": False,
        })
    
    # Completed torrents section
    if completed_torrents:
        completed_list = []
        for t in completed_torrents:
            name = _format_title(t["name"])
            completion_time = datetime.datetime.fromtimestamp(t["completion_on"])
            completed_list.append(
                f"✅ {name} - {_format_datetime_12h(completion_time)}"
            )
        
        if completed_list:
            fields.append({
                "name": "Recent Completed Downloads",
                "value": "\n".join(completed_list),
                "inline": False,
            })
    
    # Add Last Updated field with Discord timestamp markdown for relative time
    timestamp_unix = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    fields.append({
        "name": "⬇️ Last Updated ⬇️",
        "value": f"<t:{timestamp_unix}:R>",
        "inline": False
    })

    return {
        "title": "Download Progress",
        "description": "",
        "color": 3447003,
        "fields": fields,
    }
