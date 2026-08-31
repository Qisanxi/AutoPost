"""Dev.to API client."""
import re
from typing import Dict, Any
import requests
import structlog
from ..config import Config
from ..exceptions import PublishingError

logger = structlog.get_logger(__name__)
BASE_URL = "https://dev.to/api"
REQUEST_TIMEOUT = 15


def sanitize_tags(tags: list) -> list[str]:
    """Convert arbitrary AI-generated tags to Dev.to-compatible tags."""
    clean, seen = [], set()
    for tag in tags or []:
        value = re.sub(r"[^a-z0-9]", "", str(tag).lower())[:30]
        if value and value not in seen:
            clean.append(value)
            seen.add(value)
        if len(clean) == 4:
            break
    return clean


class DevToClient:
    def __init__(self):
        self.api_key = Config.DEVTO_API_KEY
        self.session = requests.Session()
        self.session.headers.update({"api-key": self.api_key, "Content-Type": "application/json", "Accept": "application/vnd.forem.api-v1+json"})

    def publish_article(self, title: str, body: str, tags: list) -> Dict[str, Any]:
        payload = {"article": {"title": title[:128], "body_markdown": body[:100000], "published": True, "tags": sanitize_tags(tags)}}
        try:
            response = self.session.post(f"{BASE_URL}/articles", json=payload, timeout=REQUEST_TIMEOUT)
            if not response.ok:
                try:
                    error_body = response.json()
                except ValueError:
                    error_body = response.text
                logger.error("devto_publish_failed", status=response.status_code, error=error_body)
                raise PublishingError("Dev.to", f"HTTP {response.status_code}: {str(error_body)[:1000]}")
            data = response.json()
            logger.info("devto_article_published", article_id=data.get("id"), tags=payload["article"]["tags"])
            return {"success": True, "post_url": data.get("url", ""), "article_id": data.get("id")}
        except PublishingError:
            raise
        except requests.exceptions.RequestException as e:
            raise PublishingError("Dev.to", str(e)[:500])