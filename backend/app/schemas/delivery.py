"""Delivery channel schemas"""

import json
import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DeliveryChannelConfig(BaseModel):
    """Base config for delivery channels"""

    pass


class DiscordConfig(DeliveryChannelConfig):
    """Discord webhook configuration"""

    webhook_url: str = Field(..., min_length=1)

    @field_validator("webhook_url")
    @classmethod
    def validate_discord_url(cls, v: str) -> str:
        if not v.startswith("https://discord.com/api/webhooks/"):
            raise ValueError("Invalid Discord webhook URL format")
        return v


class EmailConfig(DeliveryChannelConfig):
    """Email configuration"""

    email: str = Field(..., min_length=5, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email address")
        return v


class DeliveryChannelBase(BaseModel):
    type: Literal["discord", "email"] = Field(...)
    is_enabled: bool | None = True


class DeliveryChannelCreate(DeliveryChannelBase):
    """Create delivery channel - config is passed as dict"""

    config: dict = Field(...)


class DeliveryChannelUpdate(BaseModel):
    is_enabled: bool | None = None


class DeliveryChannelResponse(DeliveryChannelBase):
    id: int
    schedule_id: int
    config: Any  # Can be dict or string from DB
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def parse_config(self) -> "DeliveryChannelResponse":
        """Parse JSON string config to dict if needed"""
        if isinstance(self.config, str):
            try:
                self.config = json.loads(self.config)
            except (json.JSONDecodeError, TypeError):
                pass
        return self


class DeliveryChannelWithValidation(BaseModel):
    """Response with validation status"""

    channel: DeliveryChannelResponse
    valid: bool
    error: str | None = None
