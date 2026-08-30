"""
Google ADK Analysis Tools — Gemini-powered repo analysis and curation.
"""

import json
from typing import Dict, Any

from google.adk.tools import tool
from google import genai

from ...config import Config
from ...exceptions import APIError

client = genai.Client(api_key=Config.GEMINI_API_KEY)
MODEL = Config.GEMINI_MODEL


@tool
def analyze_repository(readme_content: str, repo_metadata: str) -> Dict[str, Any]:
    """
    Use Gemini to deeply analyze a repository's README and metadata.
    Returns structured analysis: problem_solved, tech_stack, domain_tags,
    novelty_score (1-10), complexity, target_audience, one_liner_hook.
    Use this AFTER fetching the README.
    """
    prompt = f"""Analyze this GitHub repository and return ONLY a JSON object.

REPO METADATA: {repo_metadata}

README (first 5000 chars):
{readme_content[:5000]}

Return JSON:
{{
  "problem_solved": "string (max 300 chars)",
  "tech_stack": ["string"],
  "domain_tags": ["string"],
  "novelty_score": float (0.0 to 10.0),
  "complexity": "beginner|intermediate|advanced",
  "target_audience": "string (max 150 chars)",
  "one_liner_hook": "string (max 150 chars, catchy)",
  "key_files": ["string (max 5 files)"]
}}
"""
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        text = response.text.strip()
        # Remove markdown fences if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        return {"error": str(e), "novelty_score": 5.0}


@tool
def generate_linkedin_post(analysis_json: str) -> str:
    """
    Generate a professional LinkedIn post from repo analysis.
    Returns the full post text ready to publish.
    """
    prompt = f"""Write a LinkedIn post about this repository. Professional but conversational tone.

ANALYSIS: {analysis_json}

Requirements:
- Start with a strong hook
- 3-4 short paragraphs
- 1 specific technical insight
- End with a question or CTA
- Include 3-5 hashtags at the end
- Max 300 words
- No emojis

Return ONLY the post text."""
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating post: {e}"


@tool
def generate_devto_article(analysis_json: str) -> str:
    """
    Generate a technical Dev.to article from repo analysis.
    Returns markdown-formatted article text.
    """
    prompt = f"""Write a Dev.to article about this repository. Technical but accessible.

ANALYSIS: {analysis_json}

Requirements:
- SEO-friendly title (max 80 chars)
- Introduction: problem + why it matters
- Technical overview
- One code snippet if relevant
- a tree structure if possible
- Use cases
- Conclusion with repo link
- Use markdown
- 800-1200 words

Return ONLY the article markdown."""
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating article: {e}"