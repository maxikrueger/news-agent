"""Delivery channel endpoints"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import DeliveryChannel, Schedule
from app.schemas.delivery import DeliveryChannelCreate, DeliveryChannelResponse, DeliveryChannelUpdate
from app.services.delivery import DeliveryService

router = APIRouter(prefix="/api/schedules", tags=["delivery"])


@router.get("/{schedule_id}/channels", response_model=list[DeliveryChannelResponse])
async def list_channels(
    schedule_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List all delivery channels for a schedule"""
    # Verify schedule ownership
    schedule = (
        db.query(Schedule).filter(and_(Schedule.id == schedule_id, Schedule.user_id == user_id)).first()
    )

    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    channels = db.query(DeliveryChannel).filter(DeliveryChannel.schedule_id == schedule_id).all()

    return channels


@router.post(
    "/{schedule_id}/channels", response_model=DeliveryChannelResponse, status_code=status.HTTP_201_CREATED
)
async def create_channel(
    schedule_id: int,
    channel_create: DeliveryChannelCreate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new delivery channel for a schedule"""
    # Verify schedule ownership
    schedule = (
        db.query(Schedule).filter(and_(Schedule.id == schedule_id, Schedule.user_id == user_id)).first()
    )

    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    # Validate channel config
    if channel_create.type == "discord":
        webhook_url = channel_create.config.get("webhook_url")
        if not webhook_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Discord webhook_url is required"
            )
        if not DeliveryService.validate_discord_webhook(webhook_url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or unreachable Discord webhook URL"
            )

    elif channel_create.type == "email":
        email = channel_create.config.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")
        if not DeliveryService.validate_email(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address")

    # Create channel
    channel = DeliveryChannel(
        schedule_id=schedule_id,
        type=channel_create.type,
        config=json.dumps(channel_create.config),
        is_enabled=channel_create.is_enabled,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)

    return channel


@router.put("/{schedule_id}/channels/{channel_id}", response_model=DeliveryChannelResponse)
async def update_channel(
    schedule_id: int,
    channel_id: int,
    channel_update: DeliveryChannelUpdate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a delivery channel"""
    # Verify schedule ownership
    schedule = (
        db.query(Schedule).filter(and_(Schedule.id == schedule_id, Schedule.user_id == user_id)).first()
    )

    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    # Get and update channel
    channel = (
        db.query(DeliveryChannel)
        .filter(and_(DeliveryChannel.id == channel_id, DeliveryChannel.schedule_id == schedule_id))
        .first()
    )

    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    if channel_update.is_enabled is not None:
        channel.is_enabled = channel_update.is_enabled

    db.commit()
    db.refresh(channel)

    return channel


@router.delete("/{schedule_id}/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    schedule_id: int, channel_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete a delivery channel"""
    # Verify schedule ownership
    schedule = (
        db.query(Schedule).filter(and_(Schedule.id == schedule_id, Schedule.user_id == user_id)).first()
    )

    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    # Get and delete channel
    channel = (
        db.query(DeliveryChannel)
        .filter(and_(DeliveryChannel.id == channel_id, DeliveryChannel.schedule_id == schedule_id))
        .first()
    )

    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    db.delete(channel)
    db.commit()

    return None
