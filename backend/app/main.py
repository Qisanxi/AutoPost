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


app = FastAPI(
    title="DevRel Agent API",
    description="Autonomous content curation agent",
    version="0.4.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = ["http://localhost:5173", "http://localhost:4173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)


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
    """Run the backend-owned workflow and stream safe execution events via SSE."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    async def event_stream():
        try:
            async for event in run_agent_workflow(languages=languages, limit=limit):
                event_type = event.get("type", "message")
                payload = {key: value for key, value in event.items() if key != "type"}
                yield f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"
        except Exception as exc:
            log_safe_error("agent_run", exc)
            yield f"event: error\ndata: {json.dumps({'message': 'Agent workflow failed safely.'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# Existing endpoints remain unchanged below.
@app.post("/agent/discover", tags=["Agent"])
async def discover_repos(languages: str = "typescript,python", limit: int = 5) -> Dict[str, Any]:
    if db is None: raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        client = GitHubClient(); store = FirestoreClient()
        found = client.search_trending(languages=[l.strip() for l in languages.split(",") if l.strip()], per_page=max(1, min(limit, 30)))
        saved, duplicates_skipped = [], 0
        for repo in found:
            repo_url = repo.get("url") or ""
            if not repo_url: continue
            if store.check_duplicate(repo_url): duplicates_skipped += 1; continue
            doc_id = store.create_repo({"github_url": repo_url, "source": "github_trending", "raw_name": repo["name"], "raw_description": repo.get("description", ""), "stars": repo["stars"], "topics": repo.get("topics", []), "readme_url": repo.get("readme_url", ""), "status": "pending_analysis", "created_at": firestore.SERVER_TIMESTAMP})
            saved.append({"id": doc_id, "name": repo["name"], "url": repo_url})
        return {"status": "success", "count": len(saved), "github_found": len(found), "duplicates_skipped": duplicates_skipped, "repos": saved}
    except HTTPException: raise
    except Exception as e: log_safe_error("discover_repos", e); raise HTTPException(status_code=500, detail="Discovery failed")


@app.post("/agent/analyze/{repo_id}", tags=["Agent"])
async def analyze_repo(repo_id: str) -> Dict[str, Any]:
    if db is None: raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        doc = db.collection("discovered_repos").document(repo_id).get()
        if not doc.exists: raise HTTPException(status_code=404, detail="Repo not found")
        data = doc.to_dict(); readme = GitHubClient().fetch_readme(data.get("github_url", ""))
        if not readme:
            db.collection("discovered_repos").document(repo_id).update({"status": "failed"})
            return {"status": "failed", "reason": "No README found"}
        from google import genai
        gemini = genai.Client(api_key=Config.GEMINI_API_KEY)
        metadata = json.dumps({"name": data.get("raw_name"), "description": data.get("raw_description"), "stars": data.get("stars"), "topics": data.get("topics")})
        prompt = f'''Analyze this repo and return ONLY JSON:\nMETA: {metadata}\nREADME: {readme[:4000]}\n\nReturn: {{"problem_solved":"...","tech_stack":[],"domain_tags":[],"novelty_score":0.0,"complexity":"intermediate","target_audience":"...","one_liner_hook":"...","key_files":[]}}'''
        response = gemini.models.generate_content(model=Config.GEMINI_MODEL, contents=prompt)
        analysis_text = (response.text or "").strip().replace("```json", "").replace("```", "").strip()
        if not analysis_text: raise HTTPException(status_code=502, detail="Empty analysis response")
        analysis = RepoAnalysis(**json.loads(analysis_text)).model_dump(mode="json")
        db.collection("discovered_repos").document(repo_id).update({"analysis": analysis, "status": "analyzed", "analyzed_at": firestore.SERVER_TIMESTAMP})
        return {"status": "analyzed", "repo_id": repo_id, "analysis": analysis}
    except HTTPException: raise
    except Exception as e: log_safe_error("analyze_repo", e, {"repo_id": repo_id}); raise HTTPException(status_code=500, detail="Analysis failed")


@app.post("/agent/publish/linkedin/{repo_id}", tags=["Agent"])
async def publish_linkedin(repo_id: str) -> Dict[str, Any]:
    if db is None: raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        doc = db.collection("discovered_repos").document(repo_id).get()
        if not doc.exists: raise HTTPException(status_code=404, detail="Repo not found")
        data = doc.to_dict(); analysis = data.get("analysis", {})
        if not analysis: raise HTTPException(status_code=400, detail="Repo not analyzed yet")
        from google import genai
        response = genai.Client(api_key=Config.GEMINI_API_KEY).models.generate_content(model=Config.GEMINI_MODEL, contents=f"""Write a LinkedIn post about this repo. Professional, 3-4 paragraphs, end with question.\n\nAnalysis: {json.dumps(analysis)}\n\nReturn ONLY the post text.""")
        post_text = (response.text or "").strip()
        if not post_text: raise HTTPException(status_code=502, detail="Empty LinkedIn post response")
        result = LinkedInClient().publish_post(post_text)
        db.collection("posts").document().set({"repo_id": repo_id, "platform": "linkedin", "status": "completed" if result.get("success") else "failed", "content": {"body": post_text}, "published_url": result.get("post_url", ""), "created_at": firestore.SERVER_TIMESTAMP})
        try: DiscordClient().send_notification(f"LinkedIn post published: {result.get('post_url', 'N/A')}")
        except Exception as e: log_safe_error("discord_notification", e)
        db.collection("discovered_repos").document(repo_id).update({"status": "published", "published_at": firestore.SERVER_TIMESTAMP})
        return {"status": "published", "platform": "linkedin", "result": result}
    except HTTPException: raise
    except Exception as e: log_safe_error("publish_linkedin", e, {"repo_id": repo_id}); raise HTTPException(status_code=500, detail="Publishing failed")


@app.post("/agent/publish/devto/{repo_id}", tags=["Agent"])
async def publish_devto(repo_id: str) -> Dict[str, Any]:
    if db is None: raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        doc = db.collection("discovered_repos").document(repo_id).get()
        if not doc.exists: raise HTTPException(status_code=404, detail="Repo not found")
        data = doc.to_dict(); analysis = data.get("analysis", {})
        if not analysis: raise HTTPException(status_code=400, detail="Repo not analyzed yet")
        from google import genai
        response = genai.Client(api_key=Config.GEMINI_API_KEY).models.generate_content(model=Config.GEMINI_MODEL, contents=f"""Write a Dev.to article about this repo. Markdown, 800-1200 words.\n\nAnalysis: {json.dumps(analysis)}\n\nReturn ONLY the article markdown with title on first line as: # Title""")
        article_text = (response.text or "").strip()
        if not article_text: raise HTTPException(status_code=502, detail="Empty Dev.to article response")
        lines = article_text.split("\n"); title = lines[0].replace("#", "").strip() if lines else "DevRel Post"; body = "\n".join(lines[1:]).strip()
        if not body: raise HTTPException(status_code=502, detail="Generated Dev.to article body is empty")
        result = DevToClient().publish_article(title, body, analysis.get("domain_tags", [])[:4])
        db.collection("posts").document().set({"repo_id": repo_id, "platform": "devto", "status": "completed" if result.get("success") else "failed", "content": {"headline": title, "body": body}, "published_url": result.get("post_url", ""), "created_at": firestore.SERVER_TIMESTAMP})
        try: DiscordClient().send_notification(f"Dev.to article published: {result.get('post_url', 'N/A')}")
        except Exception as e: log_safe_error("discord_notification", e)
        db.collection("discovered_repos").document(repo_id).update({"status": "published", "published_at": firestore.SERVER_TIMESTAMP})
        return {"status": "published", "platform": "devto", "result": result}
    except HTTPException: raise
    except Exception as e: log_safe_error("publish_devto", e, {"repo_id": repo_id}); raise HTTPException(status_code=500, detail="Publishing failed")


@app.get("/agent/repos", tags=["Dashboard"])
async def list_repos(status: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    if db is None: raise HTTPException(status_code=503, detail="Database not initialized")
    if status and status not in {"pending_analysis", "analyzed", "approved", "rejected", "published", "failed"}: raise HTTPException(status_code=400, detail="Invalid status")
    query = db.collection("discovered_repos").order_by("created_at", direction=firestore.Query.DESCENDING)
    if status: query = query.where("status", "==", status)
    return [{"id": d.id, **d.to_dict()} for d in query.limit(max(1, min(limit, 50))).stream()]


@app.get("/agent/posts", tags=["Dashboard"])
async def list_posts(limit: int = 20) -> List[Dict[str, Any]]:
    if db is None: raise HTTPException(status_code=503, detail="Database not initialized")
    return [{"id": d.id, **d.to_dict()} for d in db.collection("posts").order_by("created_at", direction=firestore.Query.DESCENDING).limit(max(1, min(limit, 50))).stream()]


@app.get("/agent/stats", tags=["Dashboard"])
async def get_stats() -> Dict[str, Any]:
    if db is None: raise HTTPException(status_code=503, detail="Database not initialized")
    return {"total_repos": len(list(db.collection("discovered_repos").stream())), "total_posts": len(list(db.collection("posts").stream())), "platforms": ["linkedin", "devto", "discord"]}
