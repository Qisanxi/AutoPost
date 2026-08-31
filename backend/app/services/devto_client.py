r"""
Dev.to API client.

Handles tag sanitization (Dev.to requires lowercase alphanumeric-only tags)
and parses error response bodies for better debugging.
"""

import re
from typing import Dict, Any, List

import requests
import structlog

from ..config import Config
from ..exceptions import PublishingError

logger = structlog.get_logger(__name__)
BASE_URL = "https://dev.to/api"
REQUEST_TIMEOUT = 15

# Dev.to tag rules: lowercase, alphanumeric only, max 30 chars, no hyphens/underscores/spaces
DEVTO_TAG_RE = re.compile(r"^[a-z0-9]{1,30}$")


def sanitize_devto_tags(tags: List[str]) -> List[str]:
    """Sanitize tags for Dev.to API compliance.

    Rules:
    - Lowercase only
    - Alphanumeric characters only (a-z, 0-9)
    - Max 30 characters per tag
    - Empty results are dropped
    """
    sanitized = []
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            continue
        # Strip non-alphanumeric characters, lowercase
        clean = re.sub(r"[^a-z0-9]", "", tag.lower())
        # Truncate to 30 chars
        clean = clean[:30]
        # Skip empty results
        if clean and len(clean) >= 2:
            sanitized.append(clean)
    return sanitized[:4]  # Dev.to allows max 4 tags


class DevToClient:
    def __init__(self):
        self.api_key = Config.DEVTO_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/vnd.forem.api-v1+json",
        })

    def publish_article(self, title: str, body: str, tags: list) -> Dict[str, Any]:
        """Publish an article to Dev.to with sanitized tags.

        Tags are automatically sanitized to comply with Dev.to's requirements:
        lowercase, alphanumeric only, max 30 chars.
        """
        url = f"{BASE_URL}/articles"

        # Sanitize tags before sending
        clean_tags = sanitize_devto_tags(tags)
        if not clean_tags:
            clean_tags = ["programming"]  # Fallback default tag

        logger.info("devto_publishing", title=title[:60], tags=clean_tags)

        payload = {
            "article": {
                "title": title[:128],
                "body_markdown": body[:100000],
                "published": True,
                "tags": clean_tags,
            }
        }
        try:
            response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)

            if response.status_code >= 400:
                # Parse error response body for debuggable messages
                try:
                    error_data = response.json()
                    error_detail = str(error_data)
                    logger.error(
                        "devto_api_error",
                        status_code=response.status_code,
                        error_body=error_detail[:500],
                        tags_sent=clean_tags,
                    )
                    raise PublishingError(
                        "Dev.to",
                        f"HTTP {response.status_code}: {error_detail[:200]}"
                    )
                except (ValueError, requests.exceptions.JSONDecodeError):
                    logger.error(
                        "devto_api_error_non_json",
                        status_code=response.status_code,
                        error_text=response.text[:500],
                    )
                    raise PublishingError(
                        "Dev.to",
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )

            data = response.json()
            logger.info("devto_article_published", article_id=data.get("id"))
            return {
                "success": True,
                "post_url": data.get("url", ""),
                "article_id": data.get("id"),
            }
        except PublishingError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error("devto_request_failed", error=str(e)[:200])
            raise PublishingError("Dev.to", str(e)[:100])