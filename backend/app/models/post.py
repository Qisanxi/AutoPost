"""
Post content models.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Platform(str, Enum):
    LINKEDIN = "linkedin"
    DEVTO = "devto"
    DISCORD = "discord"


class PostStatus(str, Enum):
    QUEUED = "queued"
    PUBLISHING = "publishing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class PostContent(BaseModel):
    headline: str = Field(..., max_length=300)
    body: str = Field(..., max_length=50000)
    hashtags: List[str] = Field(default_factory=list, max_length=10)
    media_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("hashtags")
    @classmethod
    def clean_hashtags(cls, v: List[str]) -> List[str]:
        clean = []
        for tag in v:
            tag = tag.lstrip("#").strip().lower()
            if tag and len(tag) <= 50 and tag.replace("-", "").replace("_", "").isalnum():
                clean.append(tag)
        return clean[:10]


class PostRecord(BaseModel):
    repo_id: str = Field(..., min_length=5, max_length=100)
    platform: Platform
    status: PostStatus = PostStatus.QUEUED
    content: PostContent
    scheduled_at: Optional[datetime] = None
    published_url: Optional[str] = Field(default=None, max_length=500)
    engagement: dict = Field(default_factory=dict)
    retry_count: int = Field(default=0, ge=0, le=5)
    error_log: List[str] = Field(default_factory=list, max_length=5)
    created_at: datetime = Field(default_factory=datetime.utcnow)