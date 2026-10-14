"""Digest management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Digest, Schedule

router = APIRouter(prefix="/api/digests", tags=["digests"])


@router.get("", response_model=list[dict])
async def list_digests(
    user_id: int = Depends(get_current_user), db: Session = Depends(get_db), skip: int = 0, limit: int = 30
):
    """List all digests for authenticated user's schedules"""
    # Single JOIN query: digests + schedule preloaded, filtered by ownership
    digests = (
        db.query(Digest)
        .options(joinedload(Digest.schedule))
        .join(Schedule)
        .filter(Schedule.user_id == user_id)
        .order_by(desc(Digest.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": digest.id,
            "schedule_id": digest.schedule_id,
            "schedule_name": digest.schedule.name,
            "content_text": digest.content_text,
            "status": digest.status,
            "created_at": digest.created_at.isoformat(),
        }
        for digest in digests
    ]


@router.get("/{digest_id}", response_model=dict)
async def get_digest(digest_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get digest details"""
    # Ownership check BEFORE fetching content (prevents timing attacks)
    digest = (
        db.query(Digest)
        .options(joinedload(Digest.schedule))
        .join(Schedule)
        .filter(Digest.id == digest_id, Schedule.user_id == user_id)
        .first()
    )

    if not digest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Digest not found")

    return {
        "id": digest.id,
        "schedule_id": digest.schedule_id,
        "schedule_name": digest.schedule.name,
        "content_text": digest.content_text,
        "status": digest.status,
        "created_at": digest.created_at.isoformat(),
    }
