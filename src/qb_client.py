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
            tags = t.get("tags", "")
            if "tv-arr" in tags or "movies-arr" in tags:
                torrents.append({
                    "name": t.get("name", "unknown"),
                    "progress": t.get("progress", 0.0),
                    "dlspeed": t.get("dlspeed", 0),
                    "ulspeed": t.get("upspeed", 0),
                    "size": t.get("size", 0),
                    "state": t.get("state", "")
                })
        return torrents

    def get_recent_completed_torrents(self, limit: int = 5) -> List[Dict]:
        url = f"{self.base_url}/api/v2/torrents/info?filter=completed&sort=completion_on&reverse=true&limit={limit}"
        r = self.session.get(url)
        r.raise_for_status()
        items = r.json()
        torrents = []
        for t in items:
            torrents.append({
                "name": t.get("name", "unknown"),
                "completion_on": t.get("completion_on", 0),
                "size": t.get("size", 0)
            })
        return torrents[:limit]
