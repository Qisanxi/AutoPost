"""
Discord Webhook client for notifications.
"""

from typing import Dict, Any

import requests
import structlog

from ..config import Config
from ..security import validate_discord_webhook_url
from ..exceptions import APIError

logger = structlog.get_logger(__name__)
REQUEST_TIMEOUT = 10


class DiscordClient:
    def __init__(self):
        self.webhook_url = Config.DISCORD_WEBHOOK_URL
        if not validate_discord_webhook_url(self.webhook_url):
            raise ValueError("Invalid Discord webhook URL")
        self.session = requests.Session()

    def send_notification(self, message: str) -> Dict[str, Any]:
        """Send a simple text notification to Discord."""
        payload = {"content": message[:2000]}  # Discord limit
        try:
            response = self.session.post(self.webhook_url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            logger.info("discord_notification_sent")
            return {"success": True}
        except requests.exceptions.RequestException as e:
            raise APIError("Discord", str(e)[:100])

    def send_embed(self, title: str, description: str, fields: list | None = None, url: str = "") -> Dict[str, Any]:
        """Send a rich embed notification."""
        embed = {
            "title": title[:256],
            "description": description[:4096],
            "color": 0x00ff00,
            "timestamp": "",
        }
        if url:
            embed["url"] = url
        if fields:
            embed["fields"] = [{"name": f["name"][:256], "value": f["value"][:1024], "inline": False} for f in fields[:25]]

        payload = {"embeds": [embed]}
        try:
            response = self.session.post(self.webhook_url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return {"success": True}
        except requests.exceptions.RequestException as e:
            raise APIError("Discord", str(e)[:100])