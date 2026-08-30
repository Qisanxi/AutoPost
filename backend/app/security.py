"""
Security utilities — input validation, sanitization, constant-time comparison.
"""

import html
import re
import hmac
from typing import Optional
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger(__name__)

MAX_URL_LENGTH = 500
MAX_TEXT_LENGTH = 50000
GITHUB_URL_RE = re.compile(r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$")
TAG_RE = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")


def validate_github_url(url: str) -> bool:
    if not isinstance(url, str) or len(url) > MAX_URL_LENGTH:
        return False
    return bool(GITHUB_URL_RE.match(url))


def validate_tags(tags: list) -> bool:
    if not isinstance(tags, list) or len(tags) > 20:
        return False
    return all(isinstance(t, str) and TAG_RE.match(t) for t in tags)


def validate_discord_webhook_url(url: str) -> bool:
    if not isinstance(url, str) or len(url) > MAX_URL_LENGTH:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in ("discord.com", "discordapp.com")
    except Exception:
        return False


def sanitize_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    if not isinstance(text, str):
        return ""
    text = text[:max_length]
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return text.strip()


def escape_html(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return html.escape(text, quote=True)


def secure_compare(a: str, b: str) -> bool:
    """Constant-time string comparison."""
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def log_safe_error(operation: str, error: Exception, extra: Optional[dict] = None):
    safe_extra = extra or {}
    for key in list(safe_extra.keys()):
        if any(s in key.lower() for s in ["token", "secret", "key", "password", "credential"]):
            safe_extra[key] = "***REDACTED***"
    logger.error(
        "operation_failed",
        operation=operation,
        error_type=type(error).__name__,
        error_message=str(error)[:200],
        **safe_extra
    )