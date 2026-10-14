"""Run a schedule end-to-end: fetch articles, generate a digest, deliver it.

Shared by the "run now" API endpoint and the background scheduler so both
paths behave identically.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import Schedule, ScheduleSource, Source
from app.services.delivery import DeliveryService
from app.services.digest import DigestService
from app.services.schedule import ScheduleService

logger = logging.getLogger(__name__)

FALLBACK_NOTICE = (
    "⚠️ Keine Artikel in den vergangenen 24 Stunden gefunden. " "Suche nach Artikeln der letzten 7 Tage...\n\n"
)


class ScheduleRunError(Exception):
    """A schedule cannot produce a digest (no sources, no recent articles)."""


@dataclass
class RunResult:
    digest_id: int
    articles_processed: int
    deliveries: dict[str, str] = field(default_factory=dict)


class ScheduleRunner:
    @staticmethod
    def run(db: Session, schedule: Schedule) -> RunResult:
        source_ids = [
            ss.source_id for ss in db.query(ScheduleSource).filter(ScheduleSource.schedule_id == schedule.id)
        ]
        if not source_ids:
            raise ScheduleRunError("Schedule has no sources configured")

        articles = DigestService.fetch_articles_from_sources(
            db, source_ids, schedule.max_articles, max_age_hours=24
        )
        fallback_message = ""
        if not articles:
            logger.info("No articles in last 24h for schedule %s, widening to 7 days", schedule.id)
            fallback_message = FALLBACK_NOTICE
            articles = DigestService.fetch_articles_from_sources(
                db, source_ids, schedule.max_articles, max_age_hours=168
            )
        if not articles:
            raise ScheduleRunError(
                "Es gibt keine aktuellen Artikel in den konfigurierten Quellen "
                "(weder in den letzten 24 Stunden noch in den letzten 7 Tagen)"
            )

        articles = DigestService.deduplicate_articles(articles)
        source_names = [s.name for s in db.query(Source).filter(Source.id.in_(source_ids))]

        content = DigestService.generate_digest(
            articles,
            profile=schedule.profile,
            language=schedule.language,
            max_articles=schedule.max_articles,
            schedule_name=schedule.name,
            source_names=source_names,
        )
        content = fallback_message + (content or "")
        if not content.strip():
            content = (
                f"Daily News Digest – {datetime.now().strftime('%Y-%m-%d')}\n\n"
                "No content could be generated. Please check your sources."
            )

        digest = DigestService.save_digest(db, schedule.id, content)
        ScheduleService.mark_schedule_run(db, schedule.id)

        return RunResult(
            digest_id=digest.id,
            articles_processed=len(articles),
            deliveries=ScheduleRunner._deliver(schedule, content),
        )

    @staticmethod
    def _deliver(schedule: Schedule, content: str) -> dict[str, str]:
        results: dict[str, str] = {}
        for channel in schedule.delivery_channels:
            if not channel.is_enabled:
                continue
            try:
                config = json.loads(channel.config) if isinstance(channel.config, str) else channel.config
                if channel.type == "discord":
                    ok = DeliveryService.deliver_via_discord(
                        webhook_url=config.get("webhook_url"), content=content
                    )
                elif channel.type == "email":
                    ok = DeliveryService.deliver_via_email(
                        email=config.get("email"),
                        subject=f"News Digest – {datetime.now().strftime('%Y-%m-%d')}",
                        html_content=content,
                    )
                else:
                    logger.warning("Unknown delivery channel type: %s", channel.type)
                    continue
                results[channel.type] = "sent" if ok else "failed"
            except Exception as e:
                logger.error("Error sending digest via %s: %s", channel.type, e)
                results[channel.type] = f"error: {str(e)[:50]}"
        return results
