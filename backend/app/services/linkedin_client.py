"""
LinkedIn Personal Profile API Client (w_member_social scope).
Posts directly to your personal profile — no company page needed.
"""

from typing import Dict, Any

import requests
import structlog

from ..config import Config
from ..exceptions import APIError, PublishingError

logger = structlog.get_logger(__name__)
LINKEDIN_API_VERSION = "202606"
REQUEST_TIMEOUT = 15


class LinkedInClient:
    BASE_URL = "https://api.linkedin.com"

    def __init__(self):
        self.access_token = Config.LINKEDIN_ACCESS_TOKEN
        self.person_urn = Config.LINKEDIN_PERSON_URN
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": LINKEDIN_API_VERSION,
            "Content-Type": "application/json",
        })

    def publish_post(self, text: str) -> Dict[str, Any]:
        """Publish a text post to your personal LinkedIn profile."""
        if not self.person_urn:
            raise PublishingError("LinkedIn", "LINKEDIN_PERSON_URN not configured")

        url = f"{self.BASE_URL}/rest/posts"
        payload = {
            "author": self.person_urn,
            "commentary": text[:3000],  # LinkedIn limit
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED"
        }

        try:
            response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            if response.status_code == 201:
                post_urn = response.headers.get("x-restli-id", "")
                post_url = f"https://www.linkedin.com/feed/update/{post_urn}"
                logger.info("linkedin_post_published", post_urn=post_urn)
                return {"success": True, "post_url": post_url, "post_urn": post_urn}
            else:
                error_text = response.text[:200]
                logger.error("linkedin_post_failed", status=response.status_code, error=error_text)
                raise PublishingError("LinkedIn", error_text)
        except requests.exceptions.RequestException as e:
            raise APIError("LinkedIn", str(e)[:100])

    def get_profile(self) -> Dict[str, Any]:
        """Get your profile info (useful for finding your person URN)."""
        url = f"{self.BASE_URL}/v2/me"
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError("LinkedIn", str(e)[:100])