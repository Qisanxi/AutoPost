"""
Secure GitHub API client.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

import base64

import requests
import structlog

from ..config import Config
from ..security import validate_github_url, log_safe_error
from ..exceptions import APIError, RateLimitError, ValidationError

logger = structlog.get_logger(__name__)
REQUEST_TIMEOUT = 15
MAX_README_LENGTH = 8000


class GitHubClient:
    BASE_URL = "https://api.github.com"
    RAW_URL = "https://raw.githubusercontent.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or Config.GITHUB_TOKEN
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevRel-Agent/1.0",
        })
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.BASE_URL}{endpoint}"
        try:
            kwargs.setdefault("timeout", REQUEST_TIMEOUT)
            response = self.session.request(method, url, **kwargs)
            if response.status_code == 403 and "rate limit" in response.text.lower():
                raise RateLimitError("GitHub")
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            raise APIError("GitHub", "Request timed out", 408)
        except requests.exceptions.RequestException as e:
            log_safe_error("github_request", e, {"endpoint": endpoint})
            raise APIError("GitHub", str(e)[:100])

    def search_trending(
        self,
        languages: Optional[List[str]] = None,
        created_after: Optional[str] = None,
        min_stars: int = 50,
        per_page: int = 10
    ) -> List[Dict[str, Any]]:
        if languages is None:
            languages = ["typescript", "python", "rust"]
        if created_after is None:
            created_after = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        if not (1 <= per_page <= 30):
            per_page = 10

        language_filter = " OR ".join(f"language:{language}" for language in languages)
        query = f"created:>{created_after} stars:>{min_stars}"
        if language_filter:
            query = f"{query} ({language_filter})"

        logger.info("github_search", languages=languages, min_stars=min_stars)
        response = self._request(
            "GET", "/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
        )

        items = response.json().get("items", [])
        results = []
        for item in items:
            url = item.get("html_url", "")
            if not validate_github_url(url):
                continue
            full_name = item.get("full_name", "")
            results.append({
                "url": url,
                "name": item.get("name", ""),
                "full_name": full_name,
                "description": (item.get("description") or "")[:500],
                "stars": item.get("stargazers_count", 0),
                "topics": item.get("topics", [])[:20],
                "language": item.get("language", ""),
            })
        return results

    def fetch_readme(self, repo_url: str) -> str:
        """Fetch README via GitHub Contents API.

        Uses GET /repos/{owner}/{repo}/readme which auto-detects:
        - the default branch (any name, not just main/master)
        - the README filename (README.md, readme.md, README.rst, etc.)
        Returns Base64-decoded content up to MAX_README_LENGTH.
        """
        if not validate_github_url(repo_url):
            raise ValidationError("repo_url", "Invalid GitHub URL")
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip("/").split("/")
        repo_name = path_parts[1].replace(".git", "") if len(path_parts) >= 2 else ""
        if len(path_parts) < 2 or not repo_name:
            raise ValidationError("repo_url", "Cannot parse owner/repo")
        owner, repo = path_parts[0], repo_name

        try:
            response = self._request("GET", f"/repos/{owner}/{repo}/readme")
            data = response.json()
            content_b64 = data.get("content", "")
            if not content_b64:
                logger.warning("github_readme_empty", repo_url=repo_url)
                return ""
            readme_text = base64.b64decode(content_b64.replace("\n", "")).decode("utf-8", errors="replace")
            logger.info("github_readme_fetched", repo_url=repo_url, length=len(readme_text))
            return readme_text[:MAX_README_LENGTH]
        except RateLimitError:
            raise
        except (APIError, ValidationError) as e:
            logger.warning("github_readme_fetch_failed", repo_url=repo_url, error=str(e))
            return ""