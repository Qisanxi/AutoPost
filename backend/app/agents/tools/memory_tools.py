"""
Google ADK Memory Tools — Firestore state persistence.
"""

import json
from typing import Any, Dict

from firebase_admin import firestore

from ...db.firestore_client import FirestoreClient


def get_db_client() -> FirestoreClient:
    return FirestoreClient()


def save_repo_to_firestore(repo_data: str) -> Dict[str, Any]:
    """
    Save a discovered repository to Firestore.
    Input should be a JSON string with repo fields.
    """
    try:
        data = json.loads(repo_data)
        document_id = get_db_client().create_repo(data)
        return {"success": True, "document_id": document_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_post_to_firestore(post_data: str) -> Dict[str, Any]:
    """
    Save a post record to Firestore.
    Input should be a JSON string with post fields.
    """
    try:
        data = json.loads(post_data)
        document_id = get_db_client().create_post(data)
        return {"success": True, "document_id": document_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_recent_repos(limit: int = 10) -> list:
    """
    Get recently discovered repos from Firestore.
    """
    safe_limit = max(1, min(limit, 50))
    docs = (
        get_db_client()
        .db.collection("discovered_repos")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(safe_limit)
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]
