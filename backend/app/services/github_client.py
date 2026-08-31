"""
Secure GitHub API client.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set
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
            # Handle both primary (403) and secondary (429) rate limits.
            # Previously only 403 was caught; GitHub returns 429 for secondary
            # rate limits, which fell through to raise_for_status() and became
            # a generic APIError with no retry hint.
            if response.status_code == 429 or (
                response.status_code == 403 and "rate limit" in response.text.lower()
            ):
                logger.warning(
                    "github_rate_limit_hit",
                    status=response.status_code,
                    retry_after=response.headers.get("Retry-After", "unknown"),
                    endpoint=endpoint,
                )
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

        logger.info(
            "github_search_start",
            languages=languages,
            min_stars=min_stars,
            created_after=created_after,
            per_page=per_page,
        )

        # Previously the code built a single combined query using OR grouping:
        #   created:>DATE stars:>N (language:typescript OR language:python)
        # This construction can silently return 0 results when used with
        # fine-grained tokens, because the parenthetical OR interacts poorly
        # with the date and star qualifiers under certain token scopes.
        #
        # Fix: issue one query per language and deduplicate results.
        # This is more reliable and gives per-language diagnostic logs.
        seen_urls: Set[str] = set()
        results: List[Dict[str, Any]] = []

        for language in languages:
            query = f"created:>{created_after} stars:>{min_stars} language:{language}"
            logger.info("github_search_query", query=query, language=language)

            try:
                response = self._request(
                    "GET", "/search/repositories",
                    params={"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
                )
            except RateLimitError:
                logger.warning("github_search_rate_limited_skipping_remaining", language=language)
                break
            except APIError as e:
                log_safe_error("github_search_language", e, {"language": language})
                continue

            payload = response.json()
            items = payload.get("items", [])
            total_count = payload.get("total_count", 0)
            incomplete = payload.get("incomplete_results", False)

            logger.info(
                "github_search_results",
                language=language,
                total_count=total_count,
                items_returned=len(items),
                incomplete_results=incomplete,
                query=query,
            )

            if not items:
                # Explicit warning so empty results are visible in logs instead
                # of silently returning an empty list with no diagnostic info.
                logger.warning(
                    "github_search_empty",
                    language=language,
                    total_count=total_count,
                    incomplete_results=incomplete,
                    hint="Check token scope (needs All repositories) and query params",
                    query=query,
                )

            for item in items:
                url = item.get("html_url", "")
                if not validate_github_url(url) or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append({
                    "url": url,
                    "name": item.get("name", ""),
                    "full_name": item.get("full_name", ""),
                    "description": (item.get("description") or "")[:500],
                    "stars": item.get("stargazers_count", 0),
                    "topics": item.get("topics", [])[:20],
                    "language": item.get("language", ""),
                })

        logger.info("github_search_complete", total_results=len(results), languages=languages)
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
