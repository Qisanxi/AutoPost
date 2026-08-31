"""Firestore database client with session-scoped repositories and posts."""

import re
from typing import Dict, Any, List, Optional

from firebase_admin import firestore
import structlog

from ..security import validate_github_url, validate_tags

logger = structlog.get_logger(__name__)
SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9-]{8,128}$")


class FirestoreClient:
    """Firestore client with validation and per-browser-session namespacing."""

    def __init__(self, session_id: Optional[str] = None):
        self.db = firestore.client()
        self.session_id = session_id

    def _session_doc(self):
        if not self.session_id or not SESSION_ID_RE.fullmatch(self.session_id):
            raise ValueError("Invalid session ID")
        return self.db.collection("sessions").document(self.session_id)

    def repos_collection(self):
        return self._session_doc().collection("discovered_repos")

    def posts_collection(self):
        return self._session_doc().collection("posts")

    def create_repo(self, repo_data: Dict[str, Any]) -> str:
        url = repo_data.get("github_url", "")
        if not validate_github_url(url):
            raise ValueError(f"Invalid github_url: {url}")
        source = repo_data.get("source", "github_trending")
        if source not in {"github_trending", "hacker_news", "reddit"}:
            raise ValueError(f"Invalid source: {source}")
        status = repo_data.get("status", "pending_analysis")
        if status not in {"pending_analysis", "analyzed", "approved", "rejected", "published", "failed"}:
            raise ValueError(f"Invalid status: {status}")
        clean_data = {
            "github_url": url, "source": source,
            "raw_name": str(repo_data.get("raw_name", ""))[:100],
            "raw_description": str(repo_data.get("raw_description", ""))[:500],
            "stars": max(0, int(repo_data.get("stars", 0))),
            "topics": repo_data.get("topics", [])[:20],
            "readme_url": str(repo_data.get("readme_url", ""))[:500],
            "status": status, "created_at": firestore.SERVER_TIMESTAMP,
        }
        self._session_doc().set({"updated_at": firestore.SERVER_TIMESTAMP}, merge=True)
        doc_ref = self.repos_collection().document()
        doc_ref.set(clean_data)
        return doc_ref.id

    def get_repo(self, repo_id: str) -> Optional[Dict[str, Any]]:
        doc = self.repos_collection().document(repo_id).get()
        return {"id": doc.id, **doc.to_dict()} if doc.exists else None

    def get_repos(self, status: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        query = self.repos_collection().order_by("created_at", direction=firestore.Query.DESCENDING)
        if status:
            query = query.where("status", "==", status)
        return [{"id": d.id, **d.to_dict()} for d in query.limit(min(max(limit, 1), 100)).stream()]

    def get_repos_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.get_repos(status=status, limit=limit)

    def update_repo_status(self, repo_id: str, status: str, extra_fields: Optional[Dict[str, Any]] = None) -> None:
        if status not in {"pending_analysis", "analyzed", "approved", "rejected", "published", "failed"}:
            raise ValueError(f"Invalid status: {status}")
        update_data = {"status": status}
        if extra_fields:
            for key in {"analysis", "curation", "analyzed_at", "published_at", "error_log"} & extra_fields.keys():
                update_data[key] = extra_fields[key]
        self.repos_collection().document(repo_id).update(update_data)

    def check_duplicate(self, github_url: str) -> bool:
        if not validate_github_url(github_url):
            return False
        return any(self.repos_collection().where("github_url", "==", github_url).limit(1).stream())

    def create_post(self, post_data: Dict[str, Any]) -> str:
        platform = post_data.get("platform", "")
        if platform not in {"linkedin", "devto", "discord"}:
            raise ValueError(f"Invalid platform: {platform}")
        status = post_data.get("status", "queued")
        if status not in {"queued", "publishing", "verifying", "completed", "failed"}:
            raise ValueError(f"Invalid post status: {status}")
        clean_data = {
            "repo_id": str(post_data.get("repo_id", ""))[:100], "platform": platform, "status": status,
            "content": post_data.get("content", {}), "published_url": str(post_data.get("published_url", ""))[:500],
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        doc_ref = self.posts_collection().document()
        doc_ref.set(clean_data)
        return doc_ref.id

    def get_posts(self, limit: int = 50) -> List[Dict[str, Any]]:
        docs = self.posts_collection().order_by("created_at", direction=firestore.Query.DESCENDING).limit(min(max(limit, 1), 100)).stream()
        return [{"id": d.id, **d.to_dict()} for d in docs]

    def get_posts_by_platform(self, platform: str, limit: int = 50) -> List[Dict[str, Any]]:
        return [{"id": d.id, **d.to_dict()} for d in self.posts_collection().where("platform", "==", platform).order_by("created_at", direction=firestore.Query.DESCENDING).limit(min(limit, 100)).stream()]

    # Global learning-loop and crash-recovery collections intentionally remain shared.
    def get_tag_performance(self, tag: str) -> Optional[Dict[str, Any]]:
        if not validate_tags([tag]): raise ValueError(f"Invalid tag: {tag}")
        doc = self.db.collection("tag_performance").document(tag).get()
        return {"tag": tag, **doc.to_dict()} if doc.exists else None

    def update_tag_performance(self, tag: str, engagement: Dict[str, Any]):
        if not validate_tags([tag]): raise ValueError(f"Invalid tag: {tag}")
        self.db.collection("tag_performance").document(tag).set({"tag": tag, "last_updated": firestore.SERVER_TIMESTAMP}, merge=True)

    def create_session(self, session_data: Dict[str, Any]) -> str:
        doc_ref = self.db.collection("agent_sessions").document()
        doc_ref.set({**session_data, "started_at": firestore.SERVER_TIMESTAMP})
        return doc_ref.id

    def get_latest_session(self) -> Optional[Dict[str, Any]]:
        docs = self.db.collection("agent_sessions").order_by("started_at", direction=firestore.Query.DESCENDING).limit(1).stream()
        for d in docs: return {"id": d.id, **d.to_dict()}
        return None

    def update_session(self, session_id: str, updates: Dict[str, Any]):
        self.db.collection("agent_sessions").document(session_id).update(updates)
