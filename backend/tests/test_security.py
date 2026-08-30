"""
Security utility tests.
"""

import pytest
from app.security import (
    validate_github_url,
    validate_tags,
    validate_discord_webhook_url,
    sanitize_text,
    escape_html,
    secure_compare,
)


class TestValidateGitHubUrl:
    def test_valid_url(self):
        assert validate_github_url("https://github.com/vercel/next.js") is True

    def test_invalid_url(self):
        assert validate_github_url("https://evil.com/repo") is False

    def test_too_long(self):
        assert validate_github_url("https://github.com/" + "a" * 500) is False

    def test_non_string(self):
        assert validate_github_url(123) is False


class TestValidateTags:
    def test_valid_tags(self):
        assert validate_tags(["ai-agents", "webdev", "rust"]) is True

    def test_invalid_characters(self):
        assert validate_tags(["ai agents!"]) is False

    def test_too_many(self):
        assert validate_tags(["tag"] * 25) is False


class TestValidateDiscordWebhook:
    def test_valid(self):
        assert validate_discord_webhook_url("https://discord.com/api/webhooks/123/abc") is True

    def test_invalid_domain(self):
        assert validate_discord_webhook_url("https://evil.com/webhook") is False

    def test_http_not_https(self):
        assert validate_discord_webhook_url("http://discord.com/api/webhooks/123/abc") is False


class TestSanitizeText:
    def test_truncate(self):
        long_text = "a" * 60000
        result = sanitize_text(long_text)
        assert len(result) <= 50000

    def test_remove_null_bytes(self):
        result = sanitize_text("hello\x00world")
        assert "\x00" not in result


class TestEscapeHtml:
    def test_basic_escaping(self):
        assert escape_html("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"

    def test_quotes(self):
        assert escape_html('"test"') == "&quot;test&quot;"


class TestSecureCompare:
    def test_equal_strings(self):
        assert secure_compare("secret", "secret") is True

    def test_different_strings(self):
        assert secure_compare("secret", "different") is False

    def test_non_string(self):
        assert secure_compare("secret", 123) is False