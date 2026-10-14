"""Background scheduler: runs every schedule whose next_run_at is due.

Usage:
    python -m app.scheduler           # process due schedules once (e.g. from cron)
    python -m app.scheduler --loop    # poll forever (docker-compose service)
"""

import argparse
import logging
import time

from sqlalchemy.orm import Session

from app.db.database import get_session_factory
from app.services.runner import ScheduleRunError, ScheduleRunner
from app.services.schedule import ScheduleService

logger = logging.getLogger(__name__)


def run_due_schedules(db: Session) -> int:
    """Run all due schedules. Returns how many produced a digest.

    A failing schedule is logged and skipped so it cannot block the others;
    its next_run_at still advances, otherwise it would be retried every tick.
    """
    succeeded = 0
    for schedule in ScheduleService.get_due_schedules(db):
        try:
            result = ScheduleRunner.run(db, schedule)
            succeeded += 1
            logger.info(
                "Schedule %s: digest %s (%s articles, deliveries=%s)",
                schedule.id,
                result.digest_id,
                result.articles_processed,
                result.deliveries,
            )
        except ScheduleRunError as e:
            logger.warning("Schedule %s skipped: %s", schedule.id, e)
            ScheduleService.mark_schedule_run(db, schedule.id)
        except Exception:
            logger.exception("Schedule %s failed", schedule.id)
            db.rollback()
            ScheduleService.mark_schedule_run(db, schedule.id)
    return succeeded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loop", action="store_true", help="poll continuously")
    parser.add_argument("--interval", type=int, default=60, help="poll interval in seconds")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    session_factory = get_session_factory()
    if session_factory is None:
        raise SystemExit("DATABASE_URL is not configured")

    while True:
        with session_factory() as db:
            run_due_schedules(db)
        if not args.loop:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
