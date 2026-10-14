"""Source schemas for RSS feed management"""

from datetime import datetime

from pydantic import BaseModel, HttpUrl, field_validator

AVAILABLE_CATEGORIES = ["Tech", "Business", "News", "Entertainment", "Science", "Health", "Sport"]


class SourceBase(BaseModel):
    name: str
    url: str
    category: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        try:
            HttpUrl(v)
        except Exception as e:
            raise ValueError("Invalid URL format") from e
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v and v not in AVAILABLE_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(AVAILABLE_CATEGORIES)}")
        return v


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    is_active: bool | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v and v not in AVAILABLE_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(AVAILABLE_CATEGORIES)}")
        return v


class SourceResponse(SourceBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedTestRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        try:
            HttpUrl(v)
        except Exception as e:
            raise ValueError("Invalid URL format") from e
        return v


class FeedTestResponse(BaseModel):
    valid: bool
    title: str | None = None
    entries: int = 0
    error: str | None = None


class CategoriesResponse(BaseModel):
    categories: list[str]
