"""Tests for running schedules (run-now endpoint and background scheduler)"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models import Article, DeliveryChannel, Digest, Schedule, ScheduleSource, Source, User
from app.scheduler import run_due_schedules
from app.services.runner import FALLBACK_NOTICE, ScheduleRunError, ScheduleRunner


def make_schedule(db: Session, email: str, with_source: bool = True, due: bool = False) -> Schedule:
    user = User(email=email, password_hash=hash_password("SecurePassword123"))
    db.add(user)
    db.commit()

    offset = timedelta(hours=-1) if due else timedelta(hours=1)
    schedule = Schedule(
        user_id=user.id,
        name="Morning",
        cron_expression="0 6 * * *",
        next_run_at=datetime.now(UTC) + offset,
        is_active=True,
    )
    db.add(schedule)
    db.commit()

    if with_source:
        source = Source(user_id=user.id, name="Tech Feed", url="https://example.com/feed.xml")
        db.add(source)
        db.commit()
        db.add(ScheduleSource(schedule_id=schedule.id, source_id=source.id))
        db.add(Article(source_id=source.id, title=f"Article for {email}", url=f"https://example.com/{email}"))
        db.commit()
    return schedule


def articles_of(db: Session, schedule: Schedule) -> list[Article]:
    source_ids = [ss.source_id for ss in db.query(ScheduleSource).filter_by(schedule_id=schedule.id)]
    return db.query(Article).filter(Article.source_id.in_(source_ids)).all()


class TestScheduleRunner:
    def test_run_without_sources_raises(self, db: Session):
        schedule = make_schedule(db, "runner_nosrc@test.com", with_source=False)
        with pytest.raises(ScheduleRunError, match="no sources"):
            ScheduleRunner.run(db, schedule)

    @patch("app.services.runner.DigestService.fetch_articles_from_sources", return_value=[])
    def test_run_without_articles_raises(self, _fetch, db: Session):
        schedule = make_schedule(db, "runner_noart@test.com")
        with pytest.raises(ScheduleRunError, match="keine aktuellen Artikel"):
            ScheduleRunner.run(db, schedule)

    @patch("app.services.runner.DigestService.generate_digest", return_value="Digest body")
    def test_run_saves_digest_and_delivers(self, _gen, db: Session):
        schedule = make_schedule(db, "runner_ok@test.com")
        db.add(
            DeliveryChannel(
                schedule_id=schedule.id,
                type="discord",
                config=json.dumps({"webhook_url": "https://discord.com/api/webhooks/1/x"}),
            )
        )
        db.commit()

        with (
            patch(
                "app.services.runner.DigestService.fetch_articles_from_sources",
                return_value=articles_of(db, schedule),
            ),
            patch("app.services.runner.DeliveryService.deliver_via_discord", return_value=True) as send,
        ):
            result = ScheduleRunner.run(db, schedule)

        digest = db.get(Digest, result.digest_id)
        assert digest.content_text == "Digest body"
        assert result.articles_processed == 1
        assert result.deliveries == {"discord": "sent"}
        send.assert_called_once()
        db.refresh(schedule)
        assert schedule.last_run_at is not None

    @patch("app.services.runner.DigestService.generate_digest", return_value="Older news")
    def test_run_falls_back_to_last_week(self, _gen, db: Session):
        schedule = make_schedule(db, "runner_fallback@test.com")
        articles = articles_of(db, schedule)

        with patch(
            "app.services.runner.DigestService.fetch_articles_from_sources", side_effect=[[], articles]
        ) as fetch:
            result = ScheduleRunner.run(db, schedule)

        assert fetch.call_args_list[1].kwargs["max_age_hours"] == 168
        assert db.get(Digest, result.digest_id).content_text == FALLBACK_NOTICE + "Older news"


class TestRunNowEndpoint:
    def _auth(self, schedule: Schedule) -> dict:
        return {"Authorization": f"Bearer {create_access_token(user_id=schedule.user_id)}"}

    def test_run_now_without_sources_returns_400(self, client, db: Session):
        schedule = make_schedule(db, "endpoint_nosrc@test.com", with_source=False)
        response = client.post(f"/api/schedules/{schedule.id}/run", headers=self._auth(schedule))
        assert response.status_code == 400
        assert "no sources" in response.json()["detail"]

    @patch("app.services.runner.DigestService.generate_digest", return_value="Digest body")
    def test_run_now_success(self, _gen, client, db: Session):
        schedule = make_schedule(db, "endpoint_ok@test.com")
        with patch(
            "app.services.runner.DigestService.fetch_articles_from_sources",
            return_value=articles_of(db, schedule),
        ):
            response = client.post(f"/api/schedules/{schedule.id}/run", headers=self._auth(schedule))

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["articles_processed"] == 1

    def test_run_now_foreign_schedule_is_404(self, client, db: Session):
        schedule = make_schedule(db, "endpoint_owner@test.com")
        intruder = make_schedule(db, "endpoint_intruder@test.com", with_source=False)
        response = client.post(f"/api/schedules/{schedule.id}/run", headers=self._auth(intruder))
        assert response.status_code == 404


class TestScheduler:
    @patch("app.services.runner.DigestService.generate_digest", return_value="Scheduled digest")
    def test_due_schedule_is_run_and_rescheduled(self, _gen, db: Session):
        schedule = make_schedule(db, "scheduler_due@test.com", due=True)
        not_due = make_schedule(db, "scheduler_future@test.com", due=False)
        articles = articles_of(db, schedule)

        with patch("app.services.runner.DigestService.fetch_articles_from_sources", return_value=articles):
            run_due_schedules(db)

        assert db.query(Digest).filter_by(schedule_id=schedule.id).count() == 1
        assert db.query(Digest).filter_by(schedule_id=not_due.id).count() == 0
        db.refresh(schedule)
        assert schedule.last_run_at is not None

    def test_failing_schedule_does_not_block_others_and_advances(self, db: Session):
        broken = make_schedule(db, "scheduler_broken@test.com", with_source=False, due=True)
        run_due_schedules(db)
        db.refresh(broken)
        assert broken.last_run_at is not None
        assert db.query(Digest).filter_by(schedule_id=broken.id).count() == 0
