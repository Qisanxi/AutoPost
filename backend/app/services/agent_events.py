from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from firebase_admin import firestore
from google import genai

from ..config import Config
from ..db.firestore_client import FirestoreClient
from ..models.repo import RepoAnalysis
from .github_client import GitHubClient


async def run_agent_workflow(
    languages: str = "typescript,python",
    limit: int = 5,
) -> AsyncGenerator[dict[str, Any], None]:
    """Discover, deduplicate, analyze one repo, and generate reviewable drafts.

    Events intentionally describe observable execution steps rather than hidden model
    reasoning. Publishing remains an explicit user action handled by existing routes.
    """
    safe_limit = max(1, min(limit, 30))
    language_list = [item.strip() for item in languages.split(",") if item.strip()]
    github = GitHubClient()
    store = FirestoreClient()

    yield {"type": "step", "step": "discover", "status": "running", "message": "Searching GitHub for trending repositories."}
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
            yield {"type": "log", "level": "warning", "message": f"Skipped duplicate: {repo.get('name', 'unknown repository')}."}
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
        saved.append({"id": repo_id, "name": repo.get("name", ""), "url": repo_url, "metadata": payload})
        yield {"type": "log", "level": "info", "message": f"Saved {repo.get('name', 'repository')} to Firestore."}

    yield {"type": "step", "step": "discover", "status": "done", "message": f"Discovery complete: {len(saved)} saved, {duplicates} duplicates skipped."}

    if not saved:
        yield {"type": "completed", "message": "Discovery completed, but no new repository was available for analysis."}
        return

    selected = saved[0]
    repo_name = selected["name"] or "selected repository"

    yield {"type": "step", "step": "analyze", "status": "running", "message": f"Fetching README for {repo_name}."}
    readme = await asyncio.to_thread(github.fetch_readme, selected["url"])
    if not readme:
        yield {"type": "step", "step": "analyze", "status": "failed", "message": "No README was available for the selected repository."}
        yield {"type": "completed", "message": "Workflow finished without publishing. Select another repository and retry analysis."}
        return

    yield {"type": "log", "level": "info", "message": "Sending repository metadata and README to Gemini for analysis."}
    metadata = selected["metadata"]
    prompt = f'''Analyze this repo and return ONLY JSON:\nMETA: {json.dumps({"name": metadata.get("raw_name"), "description": metadata.get("raw_description"), "stars": metadata.get("stars"), "topics": metadata.get("topics")})}\nREADME: {readme[:4000]}\n\nReturn: {{"problem_solved":"...","tech_stack":[],"domain_tags":[],"novelty_score":0.0,"complexity":"intermediate","target_audience":"...","one_liner_hook":"...","key_files":[]}}'''
    gemini = genai.Client(api_key=Config.GEMINI_API_KEY)
    response = await asyncio.to_thread(gemini.models.generate_content, model=Config.GEMINI_MODEL, contents=prompt)
    analysis_text = (response.text or "").strip().replace("```json", "").replace("```", "").strip()
    analysis = RepoAnalysis(**json.loads(analysis_text)).model_dump(mode="json")
    await asyncio.to_thread(store.db.collection("discovered_repos").document(selected["id"]).update, {"analysis": analysis, "status": "analyzed", "analyzed_at": firestore.SERVER_TIMESTAMP})
    yield {"type": "step", "step": "analyze", "status": "done", "message": f"Analysis completed for {repo_name}."}

    yield {"type": "step", "step": "generate", "status": "running", "message": "Generating LinkedIn and Dev.to drafts for review."}
    linkedin_prompt = f'''Write a LinkedIn post about this repository analysis. Professional, 3-4 paragraphs, end with a question. Return ONLY the post text.\n\nAnalysis: {json.dumps(analysis)}'''
    devto_prompt = f'''Write a Dev.to article about this repository analysis. Markdown, 800-1200 words. Put the title on the first line as # Title. Return ONLY the article markdown.\n\nAnalysis: {json.dumps(analysis)}'''
    linkedin_response = await asyncio.to_thread(gemini.models.generate_content, model=Config.GEMINI_MODEL, contents=linkedin_prompt)
    devto_response = await asyncio.to_thread(gemini.models.generate_content, model=Config.GEMINI_MODEL, contents=devto_prompt)
    linkedin_draft = (linkedin_response.text or "").strip()
    devto_draft = (devto_response.text or "").strip()
    if not linkedin_draft or not devto_draft:
        raise RuntimeError("Draft generation returned an empty response")

    yield {"type": "step", "step": "generate", "status": "done", "message": "Drafts generated. Publishing requires explicit approval."}
    yield {"type": "result", "repo": {"id": selected["id"], "name": repo_name, "url": selected["url"]}, "analysis": analysis, "drafts": {"linkedin": linkedin_draft, "devto": devto_draft}, "github_found": len(repos), "duplicates_skipped": duplicates}
    yield {"type": "completed", "message": "Agent workflow completed. Review the generated drafts before publishing."}
