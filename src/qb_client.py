import requests
from typing import List, Dict

class QBClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8080", username: str | None = None, password: str | None = None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()

    def login(self) -> bool:
        if not self.username and not self.password:
            return True
        url = f"{self.base_url}/api/v2/auth/login"
        r = self.session.post(url, data={"username": self.username or "", "password": self.password or ""})
        return r.status_code == 200 and r.text != "Fails."

    def get_active_torrents(self) -> List[Dict]:
        url = f"{self.base_url}/api/v2/torrents/info?filter=active"
        r = self.session.get(url)
        r.raise_for_status()
        items = r.json()
        torrents = []
        for t in items:
            progress = t.get("progress", 0.0)
            if progress >= 0.9999:
                torrents.append({
                    "name": t.get("name", "unknown"),
                    "completion_on": t.get("completion_on", 0),
                    "size": t.get("size", 0)
                })
                    "state": t.get("state", "")
                })
        return torrents

    def get_recent_completed_torrents(self, limit: int = 5) -> List[Dict]:
        url = f"{self.base_url}/api/v2/torrents/info?filter=all"
        r = self.session.get(url)
        r.raise_for_status()
        items = r.json()
        torrents = []
        for t in items:
            # Filter by progress = 100% (completed)
            if t.get("progress", 0) == 1.0:
                torrents.append({
                    "name": t.get("name", "unknown"),
                    "completion_on": t.get("completion_on", 0),
                    "size": t.get("size", 0)
                })
        # Sort by completion time, most recent first
        torrents.sort(key=lambda x: x["completion_on"], reverse=True)
        return torrents[:limit]
