"""Schedule management service"""

import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from croniter import croniter
from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import Schedule, ScheduleSource, Source
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate

logger = logging.getLogger(__name__)


def next_run_after(
    cron_expression: str, tz_name: str | None = "UTC", after: datetime | None = None
) -> datetime:
    """Next fire time of a cron expression, evaluated in the schedule's time zone.

    "0 7 * * *" in Europe/Berlin fires at 07:00 local time all year, i.e. 06:00 UTC
    in winter and 05:00 UTC in summer. The result is returned in UTC for storage.
    """
    tz = ZoneInfo(tz_name or "UTC")
    base = (after or datetime.now(UTC)).astimezone(tz)
    return croniter(cron_expression, base).get_next(datetime).astimezone(UTC)


class ScheduleService:
    @staticmethod
    def create_schedule(
        db: Session, user_id: int, source_ids: list, schedule_create: ScheduleCreate
    ) -> Schedule:
        """Create a new schedule with sources"""
        # Validate cron expression
        if not croniter.is_valid(schedule_create.cron_expression):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cron expression")

        next_run = next_run_after(schedule_create.cron_expression, schedule_create.timezone)

        schedule = Schedule(
            user_id=user_id,
            name=schedule_create.name,
            cron_expression=schedule_create.cron_expression,
            timezone=schedule_create.timezone or "UTC",
            max_articles=schedule_create.max_articles or 7,
            profile=schedule_create.profile or "Allgemeine Nachrichten",
            language=schedule_create.language or "Deutsch",
            next_run_at=next_run,
            is_active=True,
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        # Add sources to schedule
        for source_id in source_ids:
            # Verify source exists and belongs to user
            source = db.query(Source).filter(and_(Source.id == source_id, Source.user_id == user_id)).first()

            if not source:
                db.delete(schedule)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"Source {source_id} not found"
                )

            schedule_source = ScheduleSource(schedule_id=schedule.id, source_id=source_id)
            db.add(schedule_source)

        db.commit()
        return schedule

    @staticmethod
    def get_schedule(db: Session, user_id: int, schedule_id: int) -> Schedule:
        """Get a schedule (only if owned by user)"""
        schedule = (
            db.query(Schedule).filter(and_(Schedule.id == schedule_id, Schedule.user_id == user_id)).first()
        )

        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

        return schedule

    @staticmethod
    def list_schedules(db: Session, user_id: int, skip: int = 0, limit: int = 100):
        """List all schedules for a user"""
        return db.query(Schedule).filter(Schedule.user_id == user_id).offset(skip).limit(limit).all()

    @staticmethod
    def update_schedule(
        db: Session, user_id: int, schedule_id: int, schedule_update: ScheduleUpdate
    ) -> Schedule:
        """Update a schedule"""
        schedule = ScheduleService.get_schedule(db, user_id, schedule_id)

        # Validate cron expression if updated
        if schedule_update.cron_expression:
            if not croniter.is_valid(schedule_update.cron_expression):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cron expression")
            schedule.cron_expression = schedule_update.cron_expression

        if schedule_update.name is not None:
            schedule.name = schedule_update.name

        if schedule_update.timezone is not None:
            schedule.timezone = schedule_update.timezone

        if schedule_update.cron_expression or schedule_update.timezone is not None:
            schedule.next_run_at = next_run_after(schedule.cron_expression, schedule.timezone)

        if schedule_update.max_articles is not None:
            schedule.max_articles = schedule_update.max_articles

        if schedule_update.is_active is not None:
            schedule.is_active = schedule_update.is_active

        if schedule_update.profile is not None:
            schedule.profile = schedule_update.profile

        if schedule_update.language is not None:
            schedule.language = schedule_update.language

        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def delete_schedule(db: Session, user_id: int, schedule_id: int) -> None:
        """Delete a schedule"""
        schedule = ScheduleService.get_schedule(db, user_id, schedule_id)
        db.delete(schedule)
        db.commit()

    @staticmethod
    def calculate_next_run(cron_expression: str, tz_name: str | None = "UTC") -> datetime | None:
        """Calculate next run time from cron expression"""
        try:
            return next_run_after(cron_expression, tz_name)
        except Exception as e:
            logger.error(f"Error calculating next run: {e}")
            return None

    @staticmethod
    def get_due_schedules(db: Session) -> list:
        """Get all schedules that are due to run"""
        now = datetime.now(UTC)
        due_schedules = (
            db.query(Schedule).filter(and_(Schedule.is_active.is_(True), Schedule.next_run_at <= now)).all()
        )

        return due_schedules

    @staticmethod
    def mark_schedule_run(db: Session, schedule_id: int) -> Schedule | None:
        """Mark schedule as run and calculate next run time"""
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

        if not schedule:
            return None

        schedule.last_run_at = datetime.now(UTC)

        schedule.next_run_at = next_run_after(schedule.cron_expression, schedule.timezone)

        db.commit()
        db.refresh(schedule)
        return schedule
