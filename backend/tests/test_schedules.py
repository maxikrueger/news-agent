"""Tests for schedule management"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import Schedule, Source, User
from app.services.schedule import ScheduleService


class TestScheduleCRUD:
    def test_create_schedule_success(self, client, db: Session):
        """Test successful schedule creation"""
        # Create user
        user = User(email="schedule@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        # Create source
        source = Source(user_id=user.id, name="TestSource", url="https://example.com/feed.rss")
        db.add(source)
        db.commit()

        # Login
        response = client.post(
            "/api/auth/login", json={"email": "schedule@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        # Create schedule
        response = client.post(
            "/api/schedules",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Daily Digest",
                "cron_expression": "0 6 * * *",
                "timezone": "UTC",
                "max_articles": 7,
                "source_ids": [source.id],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Daily Digest"
        assert data["cron_expression"] == "0 6 * * *"
        assert data["max_articles"] == 7
        assert data["next_run_at"] is not None

    def test_create_schedule_invalid_cron(self, client, db: Session):
        """Test schedule creation with invalid cron expression"""
        user = User(email="schedule2@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "schedule2@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.post(
            "/api/schedules",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Invalid Cron", "cron_expression": "invalid cron expression", "timezone": "UTC"},
        )
        assert response.status_code == 422

    def test_get_schedules_list(self, client, db: Session):
        """Test listing user's schedules"""
        # Create user
        user = User(email="listschedule@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        # Create schedules
        schedule1 = Schedule(
            user_id=user.id, name="Morning Digest", cron_expression="0 6 * * *", next_run_at=datetime.now(UTC)
        )
        schedule2 = Schedule(
            user_id=user.id,
            name="Evening Digest",
            cron_expression="0 18 * * *",
            next_run_at=datetime.now(UTC),
        )
        db.add(schedule1)
        db.add(schedule2)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "listschedule@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.get("/api/schedules", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Morning Digest"

    def test_get_schedule_detail(self, client, db: Session):
        """Test getting schedule details"""
        user = User(email="detailschedule@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        schedule = Schedule(
            user_id=user.id, name="Test Schedule", cron_expression="0 6 * * *", next_run_at=datetime.now(UTC)
        )
        db.add(schedule)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "detailschedule@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.get(f"/api/schedules/{schedule.id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == schedule.id
        assert data["name"] == "Test Schedule"

    def test_get_schedule_not_owned(self, client, db: Session):
        """Test getting schedule not owned by user"""
        user1 = User(email="user1sched@test.com", password_hash=hash_password("SecurePassword123"))
        user2 = User(email="user2sched@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user1)
        db.add(user2)
        db.commit()

        schedule = Schedule(
            user_id=user1.id,
            name="User1 Schedule",
            cron_expression="0 6 * * *",
            next_run_at=datetime.now(UTC),
        )
        db.add(schedule)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "user2sched@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.get(f"/api/schedules/{schedule.id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 404

    def test_update_schedule(self, client, db: Session):
        """Test updating a schedule"""
        user = User(email="updatescript@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        schedule = Schedule(
            user_id=user.id,
            name="Old Name",
            cron_expression="0 6 * * *",
            next_run_at=datetime.now(UTC),
            max_articles=5,
        )
        db.add(schedule)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "updatescript@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.put(
            f"/api/schedules/{schedule.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "New Name", "max_articles": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["max_articles"] == 10

    def test_delete_schedule(self, client, db: Session):
        """Test deleting a schedule"""
        user = User(email="deletescript@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        schedule = Schedule(
            user_id=user.id, name="To Delete", cron_expression="0 6 * * *", next_run_at=datetime.now(UTC)
        )
        db.add(schedule)
        db.commit()
        schedule_id = schedule.id

        response = client.post(
            "/api/auth/login", json={"email": "deletescript@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.delete(
            f"/api/schedules/{schedule_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f"/api/schedules/{schedule_id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 404


class TestCronParsing:
    def test_valid_cron_expressions(self):
        """Test validation of valid cron expressions"""
        valid_croms = [
            "0 6 * * *",  # Daily at 6 AM
            "0 6 * * 1-5",  # Weekdays at 6 AM
            "*/15 * * * *",  # Every 15 minutes
            "0 0 1 * *",  # First day of month
        ]

        for cron_expr in valid_croms:
            assert ScheduleService.calculate_next_run(cron_expr) is not None

    def test_invalid_cron_expressions(self):
        """Test validation of invalid cron expressions"""
        invalid_crons = [
            "invalid cron",
            "100 * * * *",  # Invalid minute
        ]

        for cron_expr in invalid_crons:
            result = ScheduleService.calculate_next_run(cron_expr)
            assert result is None


class TestScheduleExecutor:
    def test_get_due_schedules(self, db: Session):
        """Test getting schedules that are due"""
        user = User(email="dueschedule@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        # Create a schedule that's due now
        due_schedule = Schedule(
            user_id=user.id,
            name="Due Schedule",
            cron_expression="0 6 * * *",
            next_run_at=datetime.now(UTC) - timedelta(hours=1),  # Past time
            is_active=True,
        )

        # Create a schedule that's not due yet
        future_schedule = Schedule(
            user_id=user.id,
            name="Future Schedule",
            cron_expression="0 6 * * *",
            next_run_at=datetime.now(UTC) + timedelta(hours=1),  # Future time
            is_active=True,
        )

        db.add(due_schedule)
        db.add(future_schedule)
        db.commit()

        # Get due schedules
        due = ScheduleService.get_due_schedules(db)

        assert len(due) >= 1
        assert any(s.id == due_schedule.id for s in due)
        assert not any(s.id == future_schedule.id for s in due)

    def test_mark_schedule_run(self, db: Session):
        """Test marking schedule as run"""
        user = User(email="markrun@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        schedule = Schedule(
            user_id=user.id, name="Test Schedule", cron_expression="0 6 * * *", next_run_at=datetime.now(UTC)
        )
        db.add(schedule)
        db.commit()

        old_next_run = schedule.next_run_at

        # Mark as run
        updated = ScheduleService.mark_schedule_run(db, schedule.id)

        assert updated.last_run_at is not None
        assert updated.next_run_at > old_next_run


class TestScheduleAuthorization:
    def test_schedule_requires_auth(self, client):
        """Test that schedule endpoints require authentication"""
        response = client.get("/api/schedules")
        assert response.status_code == 403

        response = client.post("/api/schedules", json={"name": "Test", "cron_expression": "0 6 * * *"})
        assert response.status_code == 403

    def test_user_only_sees_own_schedules(self, client, db: Session):
        """Test that users only see their own schedules"""
        user1 = User(email="auth1sched@test.com", password_hash=hash_password("SecurePassword123"))
        user2 = User(email="auth2sched@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user1)
        db.add(user2)
        db.commit()

        # User1 has 2 schedules
        sched1 = Schedule(
            user_id=user1.id, name="User1 Sched1", cron_expression="0 6 * * *", next_run_at=datetime.now(UTC)
        )
        sched2 = Schedule(
            user_id=user1.id, name="User1 Sched2", cron_expression="0 12 * * *", next_run_at=datetime.now(UTC)
        )

        # User2 has 1 schedule
        sched3 = Schedule(
            user_id=user2.id, name="User2 Sched1", cron_expression="0 18 * * *", next_run_at=datetime.now(UTC)
        )

        db.add(sched1)
        db.add(sched2)
        db.add(sched3)
        db.commit()

        # Login as User1
        response = client.post(
            "/api/auth/login", json={"email": "auth1sched@test.com", "password": "SecurePassword123"}
        )
        token1 = response.json()["access_token"]

        # User1 should see only 2 schedules
        response = client.get("/api/schedules", headers={"Authorization": f"Bearer {token1}"})
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Login as User2
        response = client.post(
            "/api/auth/login", json={"email": "auth2sched@test.com", "password": "SecurePassword123"}
        )
        token2 = response.json()["access_token"]

        # User2 should see only 1 schedule
        response = client.get("/api/schedules", headers={"Authorization": f"Bearer {token2}"})
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestScheduleTimezones:
    """Cron expressions are evaluated in the schedule's own time zone"""

    def test_next_run_respects_timezone_in_winter(self):
        from zoneinfo import ZoneInfo

        from app.services.schedule import next_run_after

        after = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
        nxt = next_run_after("0 7 * * *", "Europe/Berlin", after=after)
        assert nxt == datetime(2026, 1, 16, 6, 0, tzinfo=UTC)
        assert nxt.astimezone(ZoneInfo("Europe/Berlin")).hour == 7

    def test_next_run_respects_daylight_saving_time(self):
        from app.services.schedule import next_run_after

        after = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
        nxt = next_run_after("0 7 * * *", "Europe/Berlin", after=after)
        assert nxt == datetime(2026, 7, 16, 5, 0, tzinfo=UTC)

    def test_create_with_unknown_timezone_is_rejected(self, authenticated_client):
        response = authenticated_client.post(
            "/api/schedules",
            json={"name": "Bad TZ", "cron_expression": "0 7 * * *", "timezone": "Mars/Olympus"},
        )
        assert response.status_code == 422

    def test_changing_timezone_recalculates_next_run(self, authenticated_client):
        created = authenticated_client.post(
            "/api/schedules",
            json={"name": "TZ change", "cron_expression": "0 7 * * *", "timezone": "UTC"},
        ).json()
        updated = authenticated_client.put(
            f"/api/schedules/{created['id']}", json={"timezone": "America/New_York"}
        ).json()
        assert updated["timezone"] == "America/New_York"
        assert updated["next_run_at"] != created["next_run_at"]
