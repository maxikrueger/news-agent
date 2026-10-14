"""Schedule management endpoints"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.services.runner import ScheduleRunError, ScheduleRunner
from app.services.schedule import ScheduleService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    user_id: int = Depends(get_current_user), db: Session = Depends(get_db), skip: int = 0, limit: int = 100
):
    """List all schedules for authenticated user"""
    schedules = ScheduleService.list_schedules(db, user_id, skip, limit)
    return schedules


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_create: ScheduleCreate, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Create a new schedule"""
    schedule = ScheduleService.create_schedule(db, user_id, schedule_create.source_ids or [], schedule_create)
    return schedule


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get schedule details"""
    schedule = ScheduleService.get_schedule(db, user_id, schedule_id)
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_update: ScheduleUpdate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update schedule details"""
    schedule = ScheduleService.update_schedule(db, user_id, schedule_id, schedule_update)
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete a schedule"""
    ScheduleService.delete_schedule(db, user_id, schedule_id)
    return None


@router.post("/{schedule_id}/run", status_code=status.HTTP_200_OK)
async def run_schedule_now(
    schedule_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Run a schedule immediately (generate and deliver a digest now)"""
    schedule = ScheduleService.get_schedule(db, user_id, schedule_id)
    try:
        result = ScheduleRunner.run(db, schedule)
    except ScheduleRunError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return {
        "status": "success",
        "digest_id": result.digest_id,
        "articles_processed": result.articles_processed,
        "message": f"Digest generated with {result.articles_processed} articles",
        "deliveries": result.deliveries,
    }
