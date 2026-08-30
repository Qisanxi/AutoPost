"""
Firestore Database Client — Safe wrapper with parameterized queries.
Prevents injection, enforces schema, handles errors gracefully.
"""

from typing import Dict, Any, List, Optional

from firebase_admin import firestore
import structlog

from ..security import validate_github_url, validate_tags

logger = structlog.get_logger(__name__)


class FirestoreClient:
    """Secure Firestore client with validation and safe defaults."""

    def __init__(self):
        self.db = firestore.client()

    # ─────────────────────────────────────────────────────────────────────────
    # REPOSITORIES
    # ─────────────────────────────────────────────────────────────────────────

    def create_repo(self, repo_data: Dict[str, Any]) -> str:
        """Create a new discovered repo document. Returns document ID."""
        # Validate critical fields
        url = repo_data.get("github_url", "")
        if not validate_github_url(url):
            raise ValueError(f"Invalid github_url: {url}")

        # Sanitize
        valid_sources = {"github_trending", "hacker_news", "reddit"}
        source = repo_data.get("source", "github_trending")
        if source not in valid_sources:
            raise ValueError(f"Invalid source: {source}")

        valid_statuses = {"pending_analysis", "analyzed", "approved", "rejected", "published", "failed"}
        status = repo_data.get("status", "pending_analysis")
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        clean_data = {
            "github_url": url,
            "source": source,
            "raw_name": str(repo_data.get("raw_name", ""))[:100],
            "raw_description": str(repo_data.get("raw_description", ""))[:500],
            "stars": max(0, int(repo_data.get("stars", 0))),
            "topics": repo_data.get("topics", [])[:20],
            "readme_url": str(repo_data.get("readme_url", ""))[:500],
            "status": status,
            "created_at": firestore.SERVER_TIMESTAMP,
        }

        doc_ref = self.db.collection("discovered_repos").document()
        doc_ref.set(clean_data)
        logger.info("repo_created", doc_id=doc_ref.id, name=clean_data["raw_name"])
        return doc_ref.id

    def get_repo(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Get a single repo by ID."""
        doc = self.db.collection("discovered_repos").document(repo_id).get()
        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        return None

    def get_repos_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Query repos by status. Parameterized — safe from injection."""
        # Validate status against known values
        valid_statuses = {"pending_analysis", "analyzed", "approved", "rejected", "published", "failed"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        docs = (
            self.db.collection("discovered_repos")
            .where("status", "==", status)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(min(limit, 100))
            .stream()
        )
        return [{"id": d.id, **d.to_dict()} for d in docs]

    def update_repo_status(self, repo_id: str, status: str, extra_fields: Optional[Dict[str, Any]] = None) -> None:
        """Update repo status and optional extra fields."""
        valid_statuses = {"pending_analysis", "analyzed", "approved", "rejected", "published", "failed"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        update_data = {"status": status}
        if extra_fields:
            # Only allow known safe fields
            allowed = {"analysis", "curation", "analyzed_at", "published_at", "error_log"}
            for key in extra_fields:
                if key in allowed:
                    update_data[key] = extra_fields[key]

        self.db.collection("discovered_repos").document(repo_id).update(update_data)
        logger.info("repo_status_updated", repo_id=repo_id, status=status)

    def check_duplicate(self, github_url: str) -> bool:
        """Check if a repo URL already exists."""
        if not validate_github_url(github_url):
            return False
        docs = (
            self.db.collection("discovered_repos")
            .where("github_url", "==", github_url)
            .limit(1)
            .stream()
        )
        return any(True for _ in docs)

    # ─────────────────────────────────────────────────────────────────────────
    # POSTS
    # ─────────────────────────────────────────────────────────────────────────

    def create_post(self, post_data: Dict[str, Any]) -> str:
        """Create a post record."""
        platform = post_data.get("platform", "")
        if platform not in {"linkedin", "devto", "discord"}:
            raise ValueError(f"Invalid platform: {platform}")

        valid_statuses = {"queued", "publishing", "verifying", "completed", "failed"}
        post_status = post_data.get("status", "queued")
        if post_status not in valid_statuses:
            raise ValueError(f"Invalid post status: {post_status}")

        clean_data = {
            "repo_id": str(post_data.get("repo_id", ""))[:100],
            "platform": platform,
            "status": post_status,
            "content": {
                "headline": str(post_data.get("content", {}).get("headline", ""))[:300],
                "body": str(post_data.get("content", {}).get("body", ""))[:50000],
                "hashtags": post_data.get("content", {}).get("hashtags", [])[:10],
            },
            "published_url": str(post_data.get("published_url", ""))[:500],
            "engagement": post_data.get("engagement", {}),
            "retry_count": max(0, min(5, int(post_data.get("retry_count", 0)))),
            "created_at": firestore.SERVER_TIMESTAMP,
        }

        doc_ref = self.db.collection("posts").document()
        doc_ref.set(clean_data)
        logger.info("post_created", doc_id=doc_ref.id, platform=platform)
        return doc_ref.id

    def get_posts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all posts ordered by creation time."""
        docs = (
            self.db.collection("posts")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(min(limit, 100))
            .stream()
        )
        return [{"id": d.id, **d.to_dict()} for d in docs]

    def get_posts_by_platform(self, platform: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get posts filtered by platform."""
        if platform not in {"linkedin", "devto", "discord"}:
            raise ValueError(f"Invalid platform: {platform}")

        docs = (
            self.db.collection("posts")
            .where("platform", "==", platform)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(min(limit, 100))
            .stream()
        )
        return [{"id": d.id, **d.to_dict()} for d in docs]

    # ─────────────────────────────────────────────────────────────────────────
    # TAG PERFORMANCE (Learning Loop)
    # ─────────────────────────────────────────────────────────────────────────

    def get_tag_performance(self, tag: str) -> Optional[Dict[str, Any]]:
        """Get performance data for a specific tag."""
        if not validate_tags([tag]):
            raise ValueError(f"Invalid tag: {tag}")

        doc = self.db.collection("tag_performance").document(tag).get()
        if doc.exists:
            return {"tag": tag, **doc.to_dict()}
        return None

    def update_tag_performance(self, tag: str, engagement: Dict[str, Any]):
        """Update or create tag performance record."""
        if not validate_tags([tag]):
            raise ValueError(f"Invalid tag: {tag}")

        doc_ref = self.db.collection("tag_performance").document(tag)
        doc = doc_ref.get()

        if doc.exists:
            # Incremental update
            current = doc.to_dict()
            new_count = current.get("posts_count", 0) + 1
            new_likes = current.get("total_linkedin_likes", 0) + engagement.get("linkedin_likes", 0)
            new_reactions = current.get("total_devto_reactions", 0) + engagement.get("devto_reactions", 0)

            doc_ref.update({
                "posts_count": new_count,
                "total_linkedin_likes": new_likes,
                "total_devto_reactions": new_reactions,
                "engagement_rate": (new_likes + new_reactions) / max(new_count, 1),
                "last_updated": firestore.SERVER_TIMESTAMP,
            })
        else:
            # Create new
            doc_ref.set({
                "tag": tag,
                "posts_count": 1,
                "total_linkedin_likes": engagement.get("linkedin_likes", 0),
                "total_devto_reactions": engagement.get("devto_reactions", 0),
                "engagement_rate": engagement.get("linkedin_likes", 0) + engagement.get("devto_reactions", 0),
                "last_updated": firestore.SERVER_TIMESTAMP,
            })

        logger.info("tag_performance_updated", tag=tag)

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT SESSIONS
    # ─────────────────────────────────────────────────────────────────────────

    def create_session(self, session_data: Dict[str, Any]) -> str:
        """Create an agent session record for crash recovery."""
        clean_data = {
            "status": session_data.get("status", "in_progress"),
            "current_step": session_data.get("current_step", "start"),
            "tool_call_history": session_data.get("tool_call_history", []),
            "repos_in_pipeline": session_data.get("repos_in_pipeline", []),
            "errors": session_data.get("errors", []),
            "started_at": firestore.SERVER_TIMESTAMP,
        }
        doc_ref = self.db.collection("agent_sessions").document()
        doc_ref.set(clean_data)
        return doc_ref.id

    def get_latest_session(self) -> Optional[Dict[str, Any]]:
        """Get the most recent agent session."""
        docs = (
            self.db.collection("agent_sessions")
            .order_by("started_at", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        for d in docs:
            return {"id": d.id, **d.to_dict()}
        return None

    def update_session(self, session_id: str, updates: Dict[str, Any]):
        """Update session state (for crash recovery)."""
        allowed = {"status", "current_step", "tool_call_history", "repos_in_pipeline", "errors", "completed_at"}
        clean_updates = {k: v for k, v in updates.items() if k in allowed}
        self.db.collection("agent_sessions").document(session_id).update(clean_updates)
