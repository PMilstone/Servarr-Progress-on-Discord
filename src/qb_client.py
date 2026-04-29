import requests
import time
import logging
from typing import List, Dict, Callable, Any
from functools import wraps
from colorama import Fore, Style

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 30  # seconds
PROGRESS_COMPLETION_THRESHOLD = 0.9999  # Consider >= 99.99% as complete
DOWNLOAD_STATES = {
    "downloading",
    "stalledDL",
    "metaDL",
    "forcedDL",
    "checkingDL",
    "queuedDL",
}

def retry_with_backoff(max_attempts: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    """Decorator to retry a function with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        msg = f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                        logger.warning(msg)
                        print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        msg = f"All {max_attempts} attempts failed."
                        logger.error(msg)
                        print(f"{Fore.RED}{msg}{Style.RESET_ALL}")
            
            raise last_exception
        return wrapper
    return decorator

class QBClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8080", username: str | None = None, password: str | None = None, allowed_categories: list[str] | None = None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        # None means no filtering (show all torrents)
        self.allowed_categories = [cat.lower() for cat in allowed_categories] if allowed_categories else None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()
        return False

    def close(self):
        """Explicitly close the session."""
        if self.session:
            self.session.close()

    def login(self) -> bool:
        if not self.username and not self.password:
            return True
        try:
            url = f"{self.base_url}/api/v2/auth/login"
            r = self.session.post(url, data={"username": self.username or "", "password": self.password or ""}, timeout=DEFAULT_TIMEOUT)
            return r.status_code == 200 and r.text != "Fails."
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"Cannot connect to qBittorrent at {self.base_url}\n"
                f"  → Is qBittorrent running?\n"
                f"  → Is the Web UI enabled? (Options → Web UI)\n"
                f"  → Check if URL is correct (default: http://127.0.0.1:8080)\n"
                f"  → Error: {e}"
            )
            return False
        except requests.exceptions.Timeout:
            logger.error(
                f"Connection to qBittorrent at {self.base_url} timed out after {DEFAULT_TIMEOUT}s\n"
                f"  → qBittorrent may be unresponsive or overloaded\n"
                f"  → Check if qBittorrent is running and accessible\n"
                f"  → Try increasing timeout or check network connectivity"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to qBittorrent: {e}")
            return False

    def _has_allowed_category(self, raw_category: str) -> bool:
        """Check if torrent category matches any allowed category."""
        # If no categories specified, allow all torrents
        if self.allowed_categories is None:
            return True
        
        category_text = (raw_category or "").lower()
        return any(allowed_cat in category_text for allowed_cat in self.allowed_categories)

    @retry_with_backoff(max_attempts=3, initial_delay=1.0, backoff_factor=2.0)
    def get_active_torrents(self) -> List[Dict]:
        try:
            url = f"{self.base_url}/api/v2/torrents/info?filter=active"
            r = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            r.raise_for_status()
            items = r.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error(
                    "qBittorrent API returned 403 Forbidden\n"
                    "  → Session may have expired or authentication failed\n"
                    "  → Check QB_USER and QB_PASS credentials"
                )
            raise
        except requests.exceptions.JSONDecodeError:
            logger.error(
                "Failed to parse qBittorrent API response\n"
                "  → API may be disabled or returning unexpected format\n"
                "  → Check qBittorrent Web UI settings"
            )
            raise
        torrents = []
        for t in items:
            if not self._has_allowed_category(t.get("category", "")):
                continue

            progress = t.get("progress", 0.0)
            state = t.get("state", "")
            if progress >= PROGRESS_COMPLETION_THRESHOLD or state not in DOWNLOAD_STATES:
                continue

            torrents.append({
                "name": t.get("name", "unknown"),
                "progress": progress,
                "dlspeed": t.get("dlspeed", 0),
                "ulspeed": t.get("upspeed", 0),
                "eta": t.get("eta", -1),
                "added_on": t.get("added_on", 0),
                "time_active": t.get("time_active", 0),
                "size": t.get("size", 0),
                "state": state
            })
        return torrents

    @retry_with_backoff(max_attempts=3, initial_delay=1.0, backoff_factor=2.0)
    def get_recent_completed_torrents(self, limit: int = 5) -> List[Dict]:
        url = f"{self.base_url}/api/v2/torrents/info?filter=all"
        r = self.session.get(url, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        items = r.json()
        torrents = []
        for t in items:
            if not self._has_allowed_category(t.get("category", "")):
                continue

            progress = t.get("progress", 0.0)
            if progress >= PROGRESS_COMPLETION_THRESHOLD:
                torrents.append({
                    "name": t.get("name", "unknown"),
                    "completion_on": t.get("completion_on", 0),
                    "size": t.get("size", 0)
                })
        # Sort by completion time, most recent first
        torrents.sort(key=lambda x: x["completion_on"], reverse=True)
        return torrents[:limit]
