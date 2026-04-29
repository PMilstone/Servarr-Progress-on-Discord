import requests
import time
from typing import Any, Dict, Optional
from colorama import Fore, Style

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
        Message ID if successful (new message ID for creates, same ID for edits).
        None if the operation failed.
    
    Raises:
        requests.exceptions.RequestException: If sending fails after all retries
    """
    payload: Dict[str, Any] = {"embeds": [embed]}
    if content:
        payload["content"] = content
    
    if message_id:
        # Edit existing message
        url = f"{webhook_url}/messages/{message_id}"
        method = "PATCH"
    else:
        # Send new message with ?wait=true to get message data back
        separator = "&" if "?" in webhook_url else "?"
        url = f"{webhook_url}{separator}wait=true"
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
            
            # Return message ID
            if not message_id:
                # For new messages, extract ID from response
                try:
                    response_data = r.json()
                    message_id_from_response = response_data.get("id")
                    if not message_id_from_response:
                        print(f"Warning: Response JSON did not contain 'id' field. Keys: {list(response_data.keys())}")
                        return None
                    return message_id_from_response
                except requests.exceptions.JSONDecodeError as json_err:
                    print(f"Warning: Could not parse response JSON.")
                    print(f"  Status code: {r.status_code}")
                    print(f"  Response text preview: {r.text[:200]}")
                    print(f"  Error: {json_err}")
                    return None
            else:
                # For edited messages, return the message_id we used (indicates success)
                return message_id
            
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                msg = (
                    f"Cannot connect to Discord (attempt {attempt + 1}/{max_retries})\n"
                    f"  → Check internet connection\n"
                    f"  → Verify webhook URL is correct\n"
                    f"  → Error: {e}"
                )
                print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise ConnectionError(
                    f"Failed to connect to Discord after {max_retries} attempts\n"
                    f"  → Check internet connection\n"
                    f"  → Verify WEBHOOK_URL is correct and not deleted\n"
                    f"  → Discord may be experiencing issues: https://discordstatus.com"
                ) from e
        except requests.exceptions.Timeout as e:
            if attempt < max_retries - 1:
                msg = f"Discord webhook timeout (attempt {attempt + 1}/{max_retries}): {e}"
                print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")
                time.sleep(2 ** attempt)
            else:
                raise TimeoutError(
                    f"Discord webhook timed out after {max_retries} attempts\n"
                    f"  → Discord may be slow or experiencing issues\n"
                    f"  → Check https://discordstatus.com for status"
                ) from e
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    "Discord webhook not found (404)\n"
                    "  → Webhook may have been deleted\n"
                    "  → Verify WEBHOOK_URL in .env is correct\n"
                    "  → Create a new webhook in Discord if needed"
                ) from e
            elif e.response.status_code == 401:
                raise ValueError(
                    "Discord webhook unauthorized (401)\n"
                    "  → Webhook URL is invalid or malformed\n"
                    "  → Check WEBHOOK_URL format in .env"
                ) from e
            elif attempt < max_retries - 1:
                msg = f"Discord webhook HTTP error (attempt {attempt + 1}/{max_retries}): {e}"
                print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")
                time.sleep(2 ** attempt)
            else:
                raise
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                msg = f"Discord webhook error (attempt {attempt + 1}/{max_retries}): {e}"
                print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
    
    return None
