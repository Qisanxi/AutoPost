"""
Google ADK Generation Tools — Content creation per platform.
These are separate from publishing so the agent can review before posting.
"""

import json
from typing import Dict, Any

from google import genai

from ...config import Config

MODEL = Config.GEMINI_MODEL


def get_genai_client() -> genai.Client:
    return genai.Client(api_key=Config.GEMINI_API_KEY)


def generate_content_for_platform(analysis_json: str, platform: str) -> Dict[str, Any]:
    """
    Generate platform-specific content from repo analysis.
    platform must be 'linkedin' or 'devto'.
    Returns the generated text without publishing.
    """
    try:
        analysis = json.loads(analysis_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in analysis_json"}

    if platform.lower() == "linkedin":
        return _generate_linkedin(analysis)
    elif platform.lower() == "devto":
        return _generate_devto(analysis)
    else:
        return {"error": f"Unknown platform: {platform}"}


def _generate_linkedin(analysis: dict) -> Dict[str, Any]:
    prompt = f"""Write a LinkedIn post about this repository.

Repo: {analysis.get("raw_name", "Unknown")}
Problem: {analysis.get("problem_solved", "")}
Tech: {', '.join(analysis.get("tech_stack", []))}
Hook: {analysis.get("one_liner_hook", "")}

Requirements:
- Start with the hook
- 3-4 short paragraphs
- 1 specific technical insight
- a code snippet
- a flow diagram
- End with a question
- 3-5 hashtags
- Max 300 words
- No emojis

Return ONLY the post text."""

    try:
        response = get_genai_client().models.generate_content(model=MODEL, contents=prompt)
        text = (response.text or "").strip()
        return {"success": True, "platform": "linkedin", "content": text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _generate_devto(analysis: dict) -> Dict[str, Any]:
    prompt = f"""Write a Dev.to article about this repository.

Repo: {analysis.get("raw_name", "Unknown")}
Problem: {analysis.get("problem_solved", "")}
Tech: {', '.join(analysis.get("tech_stack", []))}
Audience: {analysis.get("target_audience", "")}
Files: {', '.join(analysis.get("key_files", []))}

Requirements:
- SEO title on first line: # Title
- 800-1200 words
- Markdown format
- One code snippet if relevant
- Conclusion with repo link

Return ONLY the article markdown."""

    try:
        response = get_genai_client().models.generate_content(model=MODEL, contents=prompt)
        text = (response.text or "").strip()
        lines = text.split("\n")
        title = lines[0].replace("#", "").strip() if lines else "DevRel Post"
        body = "\n".join(lines[1:]).strip()
        return {"success": True, "platform": "devto", "title": title, "content": body}
    except Exception as e:
        return {"success": False, "error": str(e)}