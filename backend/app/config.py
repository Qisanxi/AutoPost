"""
Configuration Management — loads from environment variables with validation.
NEVER hardcode secrets. All values come from .env or Render env vars.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env only in local development (Render uses env vars directly)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


class Config:
    """Immutable configuration container."""

    # --- Gemini ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # --- GitHub ---
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_MAX_REPOS_PER_RUN: int = int(os.getenv("GITHUB_MAX_REPOS_PER_RUN", "10"))

    # --- LinkedIn (Personal Profile via w_member_social) ---
    LINKEDIN_CLIENT_ID: str = os.getenv("LINKEDIN_CLIENT_ID", "")
    LINKEDIN_CLIENT_SECRET: str = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    LINKEDIN_ACCESS_TOKEN: str = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    LINKEDIN_PERSON_URN: str = os.getenv("LINKEDIN_PERSON_URN", "")

    # --- Dev.to ---
    DEVTO_API_KEY: str = os.getenv("DEVTO_API_KEY", "")

    # --- Discord ---
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

    # --- Agent Behavior ---
    AGENT_MAX_STEPS_PER_RUN: int = int(os.getenv("AGENT_MAX_STEPS_PER_RUN", "20"))
    AGENT_CURATION_THRESHOLD: float = float(os.getenv("AGENT_CURATION_THRESHOLD", "7.5"))
    AGENT_DAILY_POST_LIMIT: int = int(os.getenv("AGENT_DAILY_POST_LIMIT", "3"))

    # --- Firebase ---
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    @classmethod
    def validate(cls) -> None:
        """Validate critical config. Raises on missing required values."""
        errors = []

        if not cls.GEMINI_API_KEY or len(cls.GEMINI_API_KEY) < 10:
            errors.append("GEMINI_API_KEY missing or too short")

        if not cls.GITHUB_TOKEN or len(cls.GITHUB_TOKEN) < 10:
            errors.append("GITHUB_TOKEN missing or too short")

        if not cls.DEVTO_API_KEY or len(cls.DEVTO_API_KEY) < 10:
            errors.append("DEVTO_API_KEY missing or too short")

        if not cls.DISCORD_WEBHOOK_URL:
            errors.append("DISCORD_WEBHOOK_URL missing")

        if not cls.LINKEDIN_ACCESS_TOKEN or len(cls.LINKEDIN_ACCESS_TOKEN) < 10:
            errors.append("LINKEDIN_ACCESS_TOKEN missing or too short")

        if not cls.LINKEDIN_PERSON_URN:
            errors.append("LINKEDIN_PERSON_URN missing (get it from /v2/me API call)")

        if cls.GITHUB_MAX_REPOS_PER_RUN < 1 or cls.GITHUB_MAX_REPOS_PER_RUN > 50:
            errors.append("GITHUB_MAX_REPOS_PER_RUN must be 1-50")

        if errors:
            raise RuntimeError("Config validation failed: " + "; ".join(errors))


# Auto-validate in production
if os.getenv("ENVIRONMENT", "development") == "production":
    Config.validate()