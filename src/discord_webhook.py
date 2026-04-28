import requests
import time
from typing import Any, Dict, Optional

def send_embed(webhook_url: str, embed: Dict[str, Any], content: Optional[str] = None, message_id: Optional[str] = None, max_retries: int = 3) -> Optional[str]:
    """
    Send or update a Discord embed with rate limit handling.
    
    Args:
        webhook_url: Discord webhook URL
        embed: Discord embed dictionary
        content: Optional message content text
        message_id: Optional message ID to edit instead of creating new
        max_retries: Maximum number of retry attempts
    
    Returns:
        Message ID if a new message was created, None if editing existing message.
    """
    payload: Dict[str, Any] = {"embeds": [embed]}
    if content:
        payload["content"] = content
    
    if message_id:
        # Edit existing message
        url = f"{webhook_url}/messages/{message_id}"
        method = "PATCH"
    else:
        # Send new message
        url = webhook_url
        method = "POST"
    
    for attempt in range(max_retries):
        try:
            if method == "PATCH":
                r = requests.patch(url, json=payload, timeout=30)
            else:
                r = requests.post(url, json=payload, timeout=30)
            
            # Handle rate limiting
            if r.status_code == 429:
                retry_after = r.json().get("retry_after", 1.0)
                print(f"Discord rate limit hit. Waiting {retry_after}s before retry...")
                time.sleep(retry_after)
                continue
            
            r.raise_for_status()
            
            # Return message ID for new messages
            if not message_id:
                try:
                    return r.json().get("id")
                except requests.exceptions.JSONDecodeError:
                    print(f"Warning: Could not parse response JSON. Response: {r.text}")
                    return None
            return None
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"Discord webhook error (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
    
    return None
