"""
Repository data models with Pydantic validation.
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class RepoStatus(str, Enum):
    PENDING_ANALYSIS = "pending_analysis"
    ANALYZED = "analyzed"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"


class RepoDiscovery(BaseModel):
    github_url: str = Field(..., max_length=500)
    source: str = Field(..., pattern=r"^(github_trending|hacker_news|reddit)$")
    raw_name: str = Field(..., max_length=100)
    raw_description: Optional[str] = Field(default=None, max_length=500)
    stars: int = Field(default=0, ge=0, le=10000000)
    topics: List[str] = Field(default_factory=list, max_length=20)
    readme_url: Optional[str] = Field(default=None, max_length=500)
    status: RepoStatus = Field(default=RepoStatus.PENDING_ANALYSIS)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("github_url")
    @classmethod
    def check_url(cls, v: str) -> str:
        if not v.startswith("https://github.com/"):
            raise ValueError("Invalid GitHub URL")
        return v


class RepoAnalysis(BaseModel):
    problem_solved: str = Field(..., max_length=1000)
    tech_stack: List[str] = Field(default_factory=list, max_length=20)
    domain_tags: List[str] = Field(default_factory=list, max_length=20)
    novelty_score: float = Field(..., ge=0.0, le=10.0)
    complexity: str = Field(..., pattern=r"^(beginner|intermediate|advanced)$")
    target_audience: str = Field(..., max_length=200)
    one_liner_hook: str = Field(..., max_length=280)
    key_files: List[str] = Field(default_factory=list, max_length=10)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class RepoCuration(BaseModel):
    repo_id: str = Field(..., min_length=5, max_length=100)
    base_score: float = Field(..., ge=0.0, le=10.0)
    tag_boost: float = Field(default=1.0, ge=0.1, le=5.0)
    final_score: float = Field(..., ge=0.0, le=50.0)
    verdict: str = Field(..., pattern=r"^(approve|reject)$")
    reason: str = Field(default="", max_length=500)
    matched_tags: List[str] = Field(default_factory=list, max_length=20)
    curated_at: datetime = Field(default_factory=datetime.utcnow)