from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from firebase_admin import firestore

from ..db.firestore_client import FirestoreClient
from .github_client import GitHubClient


async def run_agent_workflow(
    languages: str = "typescript,python",
    limit: int = 5,
) -> AsyncGenerator[dict[str, Any], None]:
    """Run discovery as one backend-owned workflow and emit safe progress events."""
    safe_limit = max(1, min(limit, 30))
    language_list = [item.strip() for item in languages.split(",") if item.strip()]

    yield {"type": "step", "step": "discover", "status": "running", "message": "Searching GitHub for trending repositories."}

    github = GitHubClient()
    store = FirestoreClient()
    repos = await asyncio.to_thread(github.search_trending, languages=language_list, per_page=safe_limit)

    yield {"type": "log", "level": "info", "message": f"GitHub returned {len(repos)} repositories."}

    saved: list[dict[str, Any]] = []
    duplicates = 0
    for repo in repos:
        repo_url = repo.get("url") or ""
        if not repo_url:
            continue
        if await asyncio.to_thread(store.check_duplicate, repo_url):
            duplicates += 1
            yield {"type": "log", "level": "warning", "message": f"Skipped duplicate: {repo.get('name', 'unknown repo')}"}
            continue

        payload = {
            "github_url": repo_url,
            "source": "github_trending",
            "raw_name": repo.get("name", ""),
            "raw_description": repo.get("description", ""),
            "stars": repo.get("stars", 0),
            "topics": repo.get("topics", []),
            "readme_url": repo.get("readme_url", ""),
            "status": "pending_analysis",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        repo_id = await asyncio.to_thread(store.create_repo, payload)
        saved.append({"id": repo_id, "name": repo.get("name", ""), "url": repo_url})
        yield {"type": "log", "level": "info", "message": f"Saved {repo.get('name', 'repository')} to Firestore."}

    yield {
        "type": "step",
        "step": "discover",
        "status": "done",
        "message": f"Discovery complete: {len(saved)} saved, {duplicates} duplicates skipped.",
    }

    yield {
        "type": "result",
        "repos": saved,
        "github_found": len(repos),
        "duplicates_skipped": duplicates,
    }

    yield {"type": "completed", "message": "Agent discovery workflow completed."}
