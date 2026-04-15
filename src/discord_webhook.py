import requests
from typing import Any, Dict, Optional

def send_embed(webhook_url: str, embed: Dict[str, Any], content: Optional[str] = None, message_id: Optional[str] = None) -> Optional[str]:
    payload: Dict[str, Any] = {"embeds": [embed]}
    if content:
        payload["content"] = content
    
    if message_id:
        # Edit existing message
        url = f"{webhook_url}/messages/{message_id}"
        r = requests.patch(url, json=payload, timeout=30)
    else:
        # Send new message
        r = requests.post(webhook_url, json=payload, timeout=30)
    
    r.raise_for_status()
    if not message_id:
        # Try to get message ID from response
        try:
            return r.json().get("id")
        except requests.exceptions.JSONDecodeError:
            print(f"Warning: Could not parse response JSON. Response: {r.text}")
            return None
    return None
