"""
Google ADK Discovery Tools — fetch repos from GitHub, HN, Reddit.
"""

from typing import List, Dict, Any, Union

from ...services.github_client import GitHubClient
from ...security import validate_github_url


def search_github_trending(language: str = "typescript", limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search GitHub for trending repositories created in the last 7 days.
    Returns list of repos with name, url, stars, topics.
    Use this FIRST to find candidate repositories.
    """
    client = GitHubClient()
    languages = [lang.strip() for lang in language.split(",") if lang.strip()]
    if not languages:
        languages = ["typescript", "python"]
    return client.search_trending(
        languages=languages,
        per_page=min(limit, 30)
    )


def fetch_repo_readme(repo_url: str) -> str:
    """
    Fetch the raw README.md content from a GitHub repository.
    Use this AFTER discovering a repo to understand what it does.
    """
    if not validate_github_url(repo_url):
        return "Error: Invalid GitHub URL"
    client = GitHubClient()
    return client.fetch_readme(repo_url)


def fetch_hacker_news_show_hn(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch recent 'Show HN' posts from Hacker News.
    Use as ALTERNATIVE source to GitHub.
    """
    import requests
    url = "https://hn.algolia.com/api/v1/search_by_date"
    safe_limit = max(1, min(limit, 20))
    params: Dict[str, Union[str, int]] = {
        "query": "Show HN",
        "tags": "story",
        "hitsPerPage": safe_limit,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        hits = response.json().get("hits", [])
        results = []
        for hit in hits:
            story_url = hit.get("url", "")
            if validate_github_url(story_url):
                results.append({
                    "url": story_url,
                    "title": hit.get("title", ""),
                    "points": hit.get("points", 0),
                    "source": "hacker_news"
                })
        return results
    except Exception as e:
        return [{"error": str(e)}]