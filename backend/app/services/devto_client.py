"""
Dev.to API client.
"""

from typing import Dict, Any

import requests
import structlog

from ..config import Config
from ..exceptions import APIError, PublishingError

logger = structlog.get_logger(__name__)
BASE_URL = "https://dev.to/api"
REQUEST_TIMEOUT = 15


class DevToClient:
    def __init__(self):
        self.api_key = Config.DEVTO_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/vnd.forem.api-v1+json",
        })
        self.session.timeout = REQUEST_TIMEOUT

    def publish_article(self, title: str, body: str, tags: list) -> Dict[str, Any]:
        """Publish an article to Dev.to."""
        url = f"{BASE_URL}/articles"
        payload = {
            "article": {
                "title": title[:128],
                "body_markdown": body[:100000],
                "published": True,
                "tags": tags[:4],
            }
        }
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info("devto_article_published", article_id=data.get("id"))
            return {
                "success": True,
                "post_url": data.get("url", ""),
                "article_id": data.get("id"),
            }
        except requests.exceptions.RequestException as e:
            raise PublishingError("Dev.to", str(e)[:100])