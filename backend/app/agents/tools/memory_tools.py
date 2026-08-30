"""
Google ADK Memory Tools — Firestore state persistence.
"""

from typing import Dict, Any

from google.adk.tools import tool
from firebase_admin import firestore

db = firestore.client()


@tool
def save_repo_to_firestore(repo_data: str) -> Dict[str, Any]:
    """
    Save a discovered repository to Firestore.
    Input should be a JSON string with repo fields.
    """
    import json
    try:
        data = json.loads(repo_data)
        doc_ref = db.collection("discovered_repos").document()
        doc_ref.set(data)
        return {"success": True, "document_id": doc_ref.id}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def save_post_to_firestore(post_data: str) -> Dict[str, Any]:
    """
    Save a post record to Firestore.
    Input should be a JSON string with post fields.
    """
    import json
    try:
        data = json.loads(post_data)
        doc_ref = db.collection("posts").document()
        doc_ref.set(data)
        return {"success": True, "document_id": doc_ref.id}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_recent_repos(limit: int = 10) -> list:
    """
    Get recently discovered repos from Firestore.
    """
    docs = db.collection("discovered_repos").order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]