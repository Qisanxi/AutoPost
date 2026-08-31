import json
import re
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import initialize_app, firestore
import structlog
from .config import Config
from .security import log_safe_error
from .services.github_client import GitHubClient
from .services.linkedin_client import LinkedInClient
from .services.devto_client import DevToClient
from .services.discord_client import DiscordClient
from .db.firestore_client import FirestoreClient
from .models.repo import RepoAnalysis
logger = structlog.get_logger(__name__)
db = None
SESSION_RE = re.compile(r"^[a-zA-Z0-9-]{8,128}$")

def session_client(x_session_id: str | None) -> FirestoreClient:
    if not x_session_id or not SESSION_RE.fullmatch(x_session_id):
        raise HTTPException(status_code=400, detail="Missing or invalid X-Session-ID")
    return FirestoreClient(x_session_id)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db
    try: initialize_app()
    except ValueError: pass
    db = firestore.client(); logger.info("app_startup_complete")
    yield; logger.info("app_shutdown")

app = FastAPI(title="DevRel Agent API", description="Autonomous content curation agent", version="0.4.0", lifespan=lifespan, docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173","http://localhost:4173","https://autopost-9c37c.web.app"], allow_credentials=True, allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"], max_age=600)

@app.get("/", tags=["Health"])
async def root(): return {"status":"ok","service":"devrel-agent","version":"0.4.0"}
@app.get("/health", tags=["Health"])
async def health_check():
    if db is None: raise HTTPException(503,"Database not initialized")
    return {"status":"healthy","database":"connected"}

@app.post("/agent/discover", tags=["Agent"])
async def discover_repos(languages: str="typescript,python", limit:int=5, x_session_id: str | None = Header(default=None)):
    try:
        fs=session_client(x_session_id); repos=GitHubClient().search_trending([l.strip() for l in languages.split(",") if l.strip()], per_page=max(1,min(limit,30))); saved=[]
        for repo in repos:
            if fs.check_duplicate(repo["url"]): continue
            doc_id=fs.create_repo({"github_url":repo["url"],"source":"github_trending","raw_name":repo["name"],"raw_description":repo.get("description", ""),"stars":repo["stars"],"topics":repo.get("topics",[]),"readme_url":repo.get("readme_url", ""),"status":"pending_analysis"})
            saved.append({"id":doc_id,"name":repo["name"],"url":repo["url"]})
        return {"status":"success","count":len(saved),"repos":saved}
    except HTTPException: raise
    except Exception as e: log_safe_error("discover_repos",e); raise HTTPException(500,"Discovery failed")

@app.post("/agent/analyze/{repo_id}", tags=["Agent"])
async def analyze_repo(repo_id:str, x_session_id: str | None = Header(default=None)):
    try:
        fs=session_client(x_session_id); data=fs.get_repo(repo_id)
        if not data: raise HTTPException(404,"Repo not found")
        readme=GitHubClient().fetch_readme(data.get("github_url",""))
        if not readme: fs.update_repo_status(repo_id,"failed"); return {"status":"failed","reason":"No README found"}
        gemini=__import__("google").genai.Client(api_key=Config.GEMINI_API_KEY)
        metadata=json.dumps({k:data.get(k) for k in ("raw_name","raw_description","stars","topics")})
        prompt=f'''Analyze this repo and return ONLY JSON:\nMETA: {metadata}\nREADME: {readme[:4000]}\nReturn: {{"problem_solved":"...","tech_stack":[],"domain_tags":[],"novelty_score":0.0,"complexity":"intermediate","target_audience":"...","one_liner_hook":"...","key_files":[]}}'''
        text=(gemini.models.generate_content(model=Config.GEMINI_MODEL,contents=prompt).text or "").strip().replace("```json","").replace("```","").strip()
        analysis=RepoAnalysis(**json.loads(text)).model_dump(mode="json")
        fs.update_repo_status(repo_id,"analyzed",{"analysis":analysis,"analyzed_at":firestore.SERVER_TIMESTAMP})
        return {"status":"analyzed","repo_id":repo_id,"analysis":analysis}
    except HTTPException: raise
    except Exception as e: log_safe_error("analyze_repo",e,{"repo_id":repo_id}); raise HTTPException(500,"Analysis failed")

async def _publish(repo_id, platform, x_session_id):
    fs=session_client(x_session_id); data=fs.get_repo(repo_id)
    if not data: raise HTTPException(404,"Repo not found")
    analysis=data.get("analysis",{})
    if not analysis: raise HTTPException(400,"Repo not analyzed yet")
    from google import genai
    gemini=genai.Client(api_key=Config.GEMINI_API_KEY)
    if platform=="linkedin":
        prompt=f"Write a LinkedIn post about this repo. Professional, 3-4 paragraphs, end with question. Return ONLY the post text.\n\nAnalysis: {json.dumps(analysis)}"
        text=(gemini.models.generate_content(model=Config.GEMINI_MODEL,contents=prompt).text or "").strip()
        result=LinkedInClient().publish_post(text); content={"body":text}
    else:
        prompt=f"Write a Dev.to article about this repo. Markdown, 800-1200 words. Return ONLY markdown with title on first line as # Title.\n\nAnalysis: {json.dumps(analysis)}"
        article=(gemini.models.generate_content(model=Config.GEMINI_MODEL,contents=prompt).text or "").strip(); lines=article.split("\n"); title=lines[0].replace("#","").strip(); body="\n".join(lines[1:]).strip()
        if not body: raise HTTPException(502,"Generated Dev.to article body is empty")
        result=DevToClient().publish_article(title,body,analysis.get("domain_tags",[])); content={"headline":title,"body":body}
    fs.create_post({"repo_id":repo_id,"platform":platform,"status":"completed" if result.get("success") else "failed","content":content,"published_url":result.get("post_url","")})
    fs.update_repo_status(repo_id,"published",{"published_at":firestore.SERVER_TIMESTAMP})
    try: DiscordClient().send_notification(f"Published to {platform}: {result.get('post_url','N/A')}")
    except Exception as e: log_safe_error("discord_notification",e)
    return {"status":"published","platform":platform,"result":result}

@app.post("/agent/publish/linkedin/{repo_id}", tags=["Agent"])
async def publish_linkedin(repo_id:str,x_session_id:str|None=Header(default=None)):
    try:return await _publish(repo_id,"linkedin",x_session_id)
    except HTTPException:raise
    except Exception as e:log_safe_error("publish_linkedin",e,{"repo_id":repo_id});raise HTTPException(500,"Publishing failed")
@app.post("/agent/publish/devto/{repo_id}", tags=["Agent"])
async def publish_devto(repo_id:str,x_session_id:str|None=Header(default=None)):
    try:return await _publish(repo_id,"devto",x_session_id)
    except HTTPException:raise
    except Exception as e:log_safe_error("publish_devto",e,{"repo_id":repo_id});raise HTTPException(500,"Publishing failed")

@app.get("/agent/repos", tags=["Dashboard"])
async def list_repos(status:str="",limit:int=20,x_session_id:str|None=Header(default=None)):
    if status and status not in {"pending_analysis","analyzed","approved","rejected","published","failed"}: raise HTTPException(400,"Invalid status")
    return session_client(x_session_id).get_repos(status,max(1,min(limit,50)))
@app.get("/agent/posts", tags=["Dashboard"])
async def list_posts(limit:int=20,x_session_id:str|None=Header(default=None)):
    return session_client(x_session_id).get_posts(max(1,min(limit,50)))
@app.get("/agent/stats", tags=["Dashboard"])
async def get_stats(x_session_id:str|None=Header(default=None)):
    fs=session_client(x_session_id); return {"total_repos":len(fs.get_repos(limit=100)),"total_posts":len(fs.get_posts(limit=100)),"platforms":["linkedin","devto","discord"]}
