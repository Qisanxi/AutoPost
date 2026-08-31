import json
import re
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import initialize_app, firestore
import structlog

from .config import Config
from .security import log_safe_error, validate_github_url
from .services.github_client import GitHubClient
from .services.linkedin_client import LinkedInClient
from .services.devto_client import DevToClient, sanitize_devto_tags
from .services.discord_client import DiscordClient
from .models.repo import RepoAnalysis

logger = structlog.get_logger(__name__)
db: firestore.Client | None = None

# Regex for a basic UUID v4 sanity-check on incoming session IDs
_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


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

origins = [
    "http://localhost:5173",
    "http://localhost:4173",
    # Production Firebase Hosting domains
    "https://autopost-9c37c.web.app",
    "https://autopost-9c37c.firebaseapp.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _require_db():
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")


def _resolve_session(x_session_id: Optional[str]) -> str:
    """
    Validate the session ID from the X-Session-ID header.
    Every request scopes its Firestore reads/writes to this session so
    each browser gets a fully isolated view of repos and posts.
    """
    if not x_session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header is required")
    if not _UUID_RE.match(x_session_id.lower()):
        raise HTTPException(status_code=400, detail="Invalid X-Session-ID format — expected UUID v4")
    return x_session_id.lower()


def _repos_col(session_id: str):
    """Session-scoped discovered_repos sub-collection."""
    return db.collection("sessions").document(session_id).collection("discovered_repos")


def _posts_col(session_id: str):
    """Session-scoped posts sub-collection."""
    return db.collection("sessions").document(session_id).collection("posts")


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root() -> Dict[str, str]:
    return {"status": "ok", "service": "devrel-agent", "version": "0.4.0"}


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    _require_db()
    try:
        docs = db.collection("health_checks").limit(1).stream()
        _ = list(docs)
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        log_safe_error("health_check", e)
        raise HTTPException(status_code=503, detail="Database connection failed")


# ─────────────────────────────────────────────────────────────────────────────
# DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/agent/discover", tags=["Agent"])
async def discover_repos(
    languages: str = "typescript,python",
    limit: int = 5,
    x_session_id: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Discover trending repos from GitHub and save to the session's Firestore namespace."""
    _require_db()
    session_id = _resolve_session(x_session_id)

    try:
        client = GitHubClient()
        lang_list = [l.strip() for l in languages.split(",") if l.strip()]
        safe_limit = max(1, min(limit, 30))
        repos = client.search_trending(languages=lang_list, per_page=safe_limit)

        repos_col = _repos_col(session_id)
        saved = []
        for repo in repos:
            # Deduplicate within this session
            existing = list(
                repos_col.where("github_url", "==", repo["url"]).limit(1).stream()
            )
            if existing:
                continue

            doc_data = {
                "github_url": repo["url"],
                "source": "github_trending",
                "raw_name": repo["name"],
                "raw_description": repo.get("description", ""),
                "stars": repo["stars"],
                "topics": repo.get("topics", []),
                "readme_url": repo.get("readme_url", ""),
                "status": "pending_analysis",
                "created_at": firestore.SERVER_TIMESTAMP,
            }
            doc_ref = repos_col.document()
            doc_ref.set(doc_data)
            saved.append({"id": doc_ref.id, "name": repo["name"], "url": repo["url"]})

        return {"status": "success", "count": len(saved), "repos": saved}
    except HTTPException:
        raise
    except Exception as e:
        log_safe_error("discover_repos", e)
        raise HTTPException(status_code=500, detail="Discovery failed")


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/agent/analyze/{repo_id}", tags=["Agent"])
async def analyze_repo(
    repo_id: str,
    x_session_id: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Fetch README and analyze a repo using Gemini."""
    _require_db()
    session_id = _resolve_session(x_session_id)

    try:
        repos_col = _repos_col(session_id)
        doc = repos_col.document(repo_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Repo not found in this session")

        data = doc.to_dict()
        repo_url = data.get("github_url", "")

        gh = GitHubClient()
        readme = gh.fetch_readme(repo_url)
        if not readme:
            repos_col.document(repo_id).update({"status": "failed"})
            return {"status": "failed", "reason": "No README found"}

        from google import genai
        gemini = genai.Client(api_key=Config.GEMINI_API_KEY)
        metadata = json.dumps({
            "name": data.get("raw_name"),
            "description": data.get("raw_description"),
            "stars": data.get("stars"),
            "topics": data.get("topics"),
        })

        prompt = f"""Analyze this repo and return ONLY JSON:
META: {metadata}
README: {readme[:4000]}

Return: {{"problem_solved":"...","tech_stack":[],"domain_tags":[],"novelty_score":0.0,"complexity":"intermediate","target_audience":"...","one_liner_hook":"...","key_files":[]}}"""

        response = gemini.models.generate_content(model=Config.GEMINI_MODEL, contents=prompt)
        analysis_text = (response.text or "").strip().replace("```json", "").replace("```", "").strip()
        if not analysis_text:
            raise HTTPException(status_code=502, detail="Empty analysis response")
        analysis = RepoAnalysis(**json.loads(analysis_text)).model_dump(mode="json")

        repos_col.document(repo_id).update({
            "analysis": analysis,
            "status": "analyzed",
            "analyzed_at": firestore.SERVER_TIMESTAMP,
        })

        return {"status": "analyzed", "repo_id": repo_id, "analysis": analysis}
    except HTTPException:
        raise
    except Exception as e:
        log_safe_error("analyze_repo", e, {"repo_id": repo_id})
        raise HTTPException(status_code=500, detail="Analysis failed")


# ─────────────────────────────────────────────────────────────────────────────
# PUBLISHING
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/agent/publish/linkedin/{repo_id}", tags=["Agent"])
async def publish_linkedin(
    repo_id: str,
    x_session_id: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Generate and publish a LinkedIn post for a repo."""
    _require_db()
    session_id = _resolve_session(x_session_id)

    try:
        repos_col = _repos_col(session_id)
        posts_col = _posts_col(session_id)

        doc = repos_col.document(repo_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Repo not found in this session")

        data = doc.to_dict()
        analysis = data.get("analysis", {})
        if not analysis:
            raise HTTPException(status_code=400, detail="Repo not analyzed yet")

        from google import genai
        gemini = genai.Client(api_key=Config.GEMINI_API_KEY)
        prompt = f"""Write a LinkedIn post about this repo. Professional, 3-4 paragraphs, end with question.

Analysis: {json.dumps(analysis)}

Return ONLY the post text."""

        response = gemini.models.generate_content(model=Config.GEMINI_MODEL, contents=prompt)
        post_text = (response.text or "").strip()
        if not post_text:
            raise HTTPException(status_code=502, detail="Empty LinkedIn post response")

        li = LinkedInClient()
        result = li.publish_post(post_text)

        post_ref = posts_col.document()
        post_ref.set({
            "repo_id": repo_id,
            "platform": "linkedin",
            "status": "completed" if result.get("success") else "failed",
            "content": {"body": post_text},
            "published_url": result.get("post_url", ""),
            "created_at": firestore.SERVER_TIMESTAMP,
        })

        try:
            dc = DiscordClient()
            dc.send_notification(f"✅ LinkedIn post published: {result.get('post_url', 'N/A')}")
        except Exception as e:
            log_safe_error("discord_notification", e)

        repos_col.document(repo_id).update({
            "status": "published",
            "published_at": firestore.SERVER_TIMESTAMP,
        })
        return {"status": "published", "platform": "linkedin", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        log_safe_error("publish_linkedin", e, {"repo_id": repo_id})
        raise HTTPException(status_code=500, detail="Publishing failed")


@app.post("/agent/publish/devto/{repo_id}", tags=["Agent"])
async def publish_devto(
    repo_id: str,
    x_session_id: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Generate and publish a Dev.to article for a repo."""
    _require_db()
    session_id = _resolve_session(x_session_id)

    try:
        repos_col = _repos_col(session_id)
        posts_col = _posts_col(session_id)

        doc = repos_col.document(repo_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Repo not found in this session")

        data = doc.to_dict()
        analysis = data.get("analysis", {})
        if not analysis:
            raise HTTPException(status_code=400, detail="Repo not analyzed yet")

        from google import genai
        gemini = genai.Client(api_key=Config.GEMINI_API_KEY)
        prompt = f"""Write a Dev.to article about this repo. Markdown, 800-1200 words.

Analysis: {json.dumps(analysis)}

Return ONLY the article markdown with title on first line as: # Title"""

        response = gemini.models.generate_content(model=Config.GEMINI_MODEL, contents=prompt)
        article_text = (response.text or "").strip()
        if not article_text:
            raise HTTPException(status_code=502, detail="Empty Dev.to article response")

        lines = article_text.split("\n")
        title = lines[0].replace("#", "").strip() if lines else analysis.get("raw_name", "DevRel Post")
        body = "\n".join(lines[1:]).strip()
        if not body:
            raise HTTPException(status_code=502, detail="Generated Dev.to article body is empty")

        # Sanitize tags — Dev.to rejects hyphens/underscores with a 500 error
        raw_tags = analysis.get("domain_tags", [])[:4]
        safe_tags = sanitize_devto_tags(raw_tags)

        devto = DevToClient()
        result = devto.publish_article(title, body, safe_tags)

        post_ref = posts_col.document()
        post_ref.set({
            "repo_id": repo_id,
            "platform": "devto",
            "status": "completed" if result.get("success") else "failed",
            "content": {"headline": title, "body": body},
            "published_url": result.get("post_url", ""),
            "created_at": firestore.SERVER_TIMESTAMP,
        })

        try:
            dc = DiscordClient()
            dc.send_notification(f"📝 Dev.to article published: {result.get('post_url', 'N/A')}")
        except Exception as e:
            log_safe_error("discord_notification", e)

        repos_col.document(repo_id).update({
            "status": "published",
            "published_at": firestore.SERVER_TIMESTAMP,
        })
        return {"status": "published", "platform": "devto", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        log_safe_error("publish_devto", e, {"repo_id": repo_id})
        raise HTTPException(status_code=500, detail="Publishing failed")


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD DATA
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/agent/repos", tags=["Dashboard"])
async def list_repos(
    status: str = "",
    limit: int = 50,
    x_session_id: Optional[str] = Header(default=None),
) -> List[Dict[str, Any]]:
    """List discovered repos for the session."""
    _require_db()
    session_id = _resolve_session(x_session_id)

    if status and status not in {"pending_analysis", "analyzed", "approved", "rejected", "published", "failed"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    repos_col = _repos_col(session_id)
    query = repos_col.order_by("created_at", direction=firestore.Query.DESCENDING)
    if status:
        query = query.where("status", "==", status)
    docs = query.limit(max(1, min(limit, 100))).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@app.get("/agent/posts", tags=["Dashboard"])
async def list_posts(
    limit: int = 20,
    x_session_id: Optional[str] = Header(default=None),
) -> List[Dict[str, Any]]:
    """List published posts for the session."""
    _require_db()
    session_id = _resolve_session(x_session_id)

    posts_col = _posts_col(session_id)
    docs = posts_col.order_by("created_at", direction=firestore.Query.DESCENDING).limit(
        max(1, min(limit, 100))
    ).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@app.get("/agent/stats", tags=["Dashboard"])
async def get_stats(
    x_session_id: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Get session statistics."""
    _require_db()
    session_id = _resolve_session(x_session_id)

    repo_count = len(list(_repos_col(session_id).stream()))
    post_count = len(list(_posts_col(session_id).stream()))
    return {
        "total_repos": repo_count,
        "total_posts": post_count,
        "platforms": ["linkedin", "devto", "discord"],
    }
