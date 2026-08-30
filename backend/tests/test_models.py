"""
Pydantic model validation tests.
"""

import pytest
from pydantic import ValidationError

from app.models.repo import RepoDiscovery, RepoAnalysis, RepoCuration
from app.models.post import PostContent, PostRecord, Platform, PostStatus


class TestRepoDiscovery:
    def test_valid_creation(self):
        repo = RepoDiscovery(
            github_url="https://github.com/vercel/next.js",
            source="github_trending",
            raw_name="next.js",
            stars=50000,
        )
        assert repo.raw_name == "next.js"
        assert repo.status.value == "pending_analysis"

    def test_invalid_url(self):
        with pytest.raises(ValidationError):
            RepoDiscovery(
                github_url="https://evil.com/repo",
                source="github_trending",
                raw_name="test",
            )

    def test_invalid_source(self):
        with pytest.raises(ValidationError):
            RepoDiscovery(
                github_url="https://github.com/test/repo",
                source="invalid_source",
                raw_name="test",
            )


class TestRepoAnalysis:
    def test_valid_analysis(self):
        analysis = RepoAnalysis(
            problem_solved="Solves routing",
            novelty_score=8.5,
            complexity="intermediate",
            target_audience="web developers",
            one_liner_hook="The future of React frameworks",
        )
        assert analysis.novelty_score == 8.5

    def test_score_out_of_range(self):
        with pytest.raises(ValidationError):
            RepoAnalysis(
                problem_solved="test",
                novelty_score=15.0,
                complexity="beginner",
                target_audience="devs",
                one_liner_hook="test",
            )

    def test_invalid_complexity(self):
        with pytest.raises(ValidationError):
            RepoAnalysis(
                problem_solved="test",
                novelty_score=5.0,
                complexity="expert",
                target_audience="devs",
                one_liner_hook="test",
            )


class TestRepoCuration:
    def test_approve(self):
        curation = RepoCuration(
            repo_id="abc123",
            base_score=8.0,
            final_score=11.2,
            verdict="approve",
        )
        assert curation.verdict == "approve"

    def test_invalid_verdict(self):
        with pytest.raises(ValidationError):
            RepoCuration(
                repo_id="abc123",
                base_score=8.0,
                final_score=11.2,
                verdict="maybe",
            )


class TestPostContent:
    def test_valid_content(self):
        post = PostContent(
            headline="Test Post",
            body="This is the body",
            hashtags=["ai", "webdev"],
        )
        assert post.hashtags == ["ai", "webdev"]

    def test_hashtag_cleaning(self):
        post = PostContent(
            headline="Test",
            body="Body",
            hashtags=["#AI", "Web-Dev", "123"],
        )
        assert post.hashtags == ["ai", "web-dev", "123"]


class TestPostRecord:
    def test_valid_record(self):
        record = PostRecord(
            repo_id="abc123",
            platform=Platform.LINKEDIN,
            content=PostContent(headline="Test", body="Body"),
        )
        assert record.status == PostStatus.QUEUED
        assert record.platform == Platform.LINKEDIN