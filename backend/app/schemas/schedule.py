"""Schedule schemas"""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter
from pydantic import BaseModel, Field, field_validator


def _validate_timezone(v: str | None) -> str | None:
    if v is None:
        return v
    try:
        ZoneInfo(v)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError(f"Unknown time zone: {v}") from e
    return v


class ScheduleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    cron_expression: str = Field(..., min_length=5, max_length=255)
    timezone: str | None = "UTC"
    max_articles: int | None = 7
    profile: str | None = "Allgemeine Nachrichten"
    language: str | None = "Deutsch"

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        if not croniter.is_valid(v):
            raise ValueError("Invalid cron expression")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        return _validate_timezone(v)


class ScheduleCreate(ScheduleBase):
    source_ids: list[int] | None = []


class ScheduleUpdate(BaseModel):
    name: str | None = None
    cron_expression: str | None = None
    timezone: str | None = None
    max_articles: int | None = None
    is_active: bool | None = None
    profile: str | None = None
    language: str | None = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        if v is not None and not croniter.is_valid(v):
            raise ValueError("Invalid cron expression")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        return _validate_timezone(v)


class ScheduleResponse(ScheduleBase):
    id: int
    user_id: int
    is_active: bool
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    created_at: datetime
    profile: str
    language: str

    model_config = {"from_attributes": True}


class ScheduleWithSources(ScheduleResponse):
    source_ids: list[int] = []
