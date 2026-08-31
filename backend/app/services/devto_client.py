"""
Dev.to API client.
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

# Dev.to tag rules: lowercase letters and digits only, max 30 chars, max 4 tags.
# Hyphens, underscores, and spaces are NOT valid — they cause a 500 from the API.
_TAG_RE = re.compile(r'[^a-z0-9]')


def sanitize_devto_tags(tags: List[str]) -> List[str]:
    """
    Strip everything Dev.to doesn't accept from each tag.
    Falls back to safe generic tags if nothing survives sanitization.
    """
    clean = []
    for tag in tags:
        sanitized = _TAG_RE.sub('', str(tag).lower())
        if sanitized and len(sanitized) <= 30:
            clean.append(sanitized)
    result = list(dict.fromkeys(clean))[:4]  # deduplicate, keep order, max 4
    if not result:
        result = ["opensource", "github", "webdev", "programming"]
    logger.info("devto_tags_sanitized", original=tags, sanitized=result)
    return result


class DevToClient:
    def __init__(self):
        self.api_key = Config.DEVTO_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/vnd.forem.api-v1+json",
        })

    def publish_article(self, title: str, body: str, tags: List[str]) -> Dict[str, Any]:
        """Publish an article to Dev.to."""
        safe_tags = sanitize_devto_tags(tags)
        url = f"{BASE_URL}/articles"
        payload = {
            "article": {
                "title": title[:128],
                "body_markdown": body[:100000],
                "published": True,
                "tags": safe_tags,
            }
        }
        try:
            response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)

            # Parse and surface Dev.to's error body before raising.
            # Previously a 422/500 from bad tags became a generic RequestException
            # with no indication of what failed.
            if not response.ok:
                try:
                    err_body = response.json()
                    err_detail = err_body.get("error") or str(err_body)
                except Exception:
                    err_detail = response.text[:300]
                logger.error(
                    "devto_publish_failed",
                    status=response.status_code,
                    detail=err_detail,
                    tags_sent=safe_tags,
                )
                raise PublishingError("Dev.to", f"HTTP {response.status_code}: {err_detail}")

            data = response.json()
            logger.info("devto_article_published", article_id=data.get("id"), tags=safe_tags)
            return {
                "success": True,
                "post_url": data.get("url", ""),
                "article_id": data.get("id"),
            }
        except PublishingError:
            raise
        except requests.exceptions.RequestException as e:
            raise PublishingError("Dev.to", str(e)[:100])
