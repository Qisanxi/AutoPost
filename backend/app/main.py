import json
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from firebase_admin import initialize_app, firestore
import structlog

from .config import Config
from .security import log_safe_error
from .services.github_client import GitHubClient
from .services.linkedin_client import LinkedInClient
from .services.devto_client import DevToClient
from .services.discord_client import DiscordClient
from .services.agent_events import run_agent_workflow
from .db.firestore_client import FirestoreClient
from .models.repo import RepoAnalysis

logger = structlog.get_logger(__name__)
db: firestore.Client | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db
    try:
        initialize_app()
    except ValueError:
        pass
    db = firestore.client()
    logger.info("app_startup_complete")
    yield
    logger.info("app_shutdown")


app = FastAPI(title="DevRel Agent API", description="Autonomous content curation agent", version="0.4.0", lifespan=lifespan, docs_url="/docs", redoc_url="/redoc")

origins = ["http://localhost:5173", "http://localhost:4173"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"], max_age=600)


@app.get("/", tags=["Health"])
async def root() -> Dict[str, str]:
    return {"status": "ok", "service": "devrel-agent", "version": "0.4.0"}


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        _ = list(db.collection("health_checks").limit(1).stream())
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        log_safe_error("health_check", e)
        raise HTTPException(status_code=503, detail="Database connection failed")


@app.post("/agent/run", tags=["Agent"])
async def run_agent(languages: str = "typescript,python", limit: int = 5):
    """Run a backend-owned agent workflow and stream safe execution events via SSE."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    async def event_stream():
        try:
            async for event in run_agent_workflow(languages=languages, limit=limit):
                event_type = event.pop("type", "message")
                payload = json.dumps(event, default=str)
                yield f"event: {event_type}\ndata: {payload}\n\n"
        except Exception as exc:
            log_safe_error("agent_run", exc)
            payload = json.dumps({"message": "Agent workflow failed safely."})
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


@app.post("/agent/discover", tags=["Agent"])
async def discover_repos(languages: str = "typescript,python", limit: int = 5) -> Dict[str, Any]:
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        client = GitHubClient()
        store = FirestoreClient()
        lang_list = [l.strip() for l in languages.split(",") if l.strip()]
        safe_limit = max(1, min(limit, 30))
        github_found = client.search_trending(languages=lang_list, per_page=safe_limit)
        duplicates_skipped = 0
        saved = []
        for repo in github_found:
            repo_url = repo.get("url") or ""
            if not repo_url:
                continue
            if store.check_duplicate(repo_url):
                duplicates_skipped += 1
                continue
            doc_data = {"github_url": repo_url, "source": "github_trending", "raw_name": repo["name"], "raw_description": repo.get("description", ""), "stars": repo["stars"], "topics": repo.get("topics", []), "readme_url": repo.get("readme_url", ""), "status": "pending_analysis", "created_at": firestore.SERVER_TIMESTAMP}
            doc_id = store.create_repo(doc_data)
            saved.append({"id": doc_id, "name": repo["name"], "url": repo_url})
        return {"status": "success", "count": len(saved), "github_found": len(github_found), "duplicates_skipped": duplicates_skipped, "repos": saved}
    except HTTPException:
        raise
    except Exception as e:
        log_safe_error("discover_repos", e)
        raise HTTPException(status_code=500, detail="Discovery failed")


@app.post("/agent/analyze/{repo_id}", tags=["Agent"])
async def analyze_repo(repo_id: str) -> Dict[str, Any]:
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        doc = db.collection("discovered_repos").document(repo_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Repo not found")
        data = doc.to_dict()
        readme = GitHubClient().fetch_readme(data.get("github_url", ""))
        if not readme:
            db.collection("discovered_repos").document(repo_id).update({"status": "failed"})
            return {"status": "failed", "reason": "No README found"}
        from google import genai
        gemini = genai.Client(api_key=Config.GEMINI_API_KEY)
        metadata = json.dumps({"name": data.get("raw_name"), "description": data.get("raw_description"), "stars": data.get("stars"), "topics": data.get("topics")})
        prompt = f'''Analyze this repository and return only valid JSON.\nMETA: {metadata}\nREADME: {readme[:4000]}\nReturn: {{"problem_solved":"...","tech_stack":[],"domain_tags":[],"novelty_score":0.0,"complexity":"intermediate","target_audience":"...","one_liner_hook":"...","key_files":[]}}'''
        response = gemini.models.generate_content(model=Config.GEMINI_MODEL, contents=prompt)
        analysis_text = (response.text or "").strip().replace("```json", "").replace("```", "").strip()
        if not analysis_text:
            raise HTTPException(status_code=502, detail="Empty analysis response")
        analysis = RepoAnalysis(**json.loads(analysis_text)).model_dump(mode="json")
        db.collection("discovered_repos").document(repo_id).update({"analysis": analysis, "status": "analyzed", "analyzed_at": firestore.SERVER_TIMESTAMP})
        return {"status": "analyzed", "repo_id": repo_id, "analysis": analysis}
    except HTTPException:
        raise
    except Exception as e:
        log_safe_error("analyze_repo", e, {"repo_id": repo_id})
        raise HTTPException(status_code=500, detail="Analysis failed")
