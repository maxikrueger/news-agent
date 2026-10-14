"""Tests for delivery service (Discord and Email)"""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import DeliveryChannel, Schedule, User
from app.services.delivery import DeliveryService


class TestDiscordDelivery:
    def test_deliver_via_discord_success(self):
        """Test successful Discord delivery"""
        webhook_url = "https://discord.com/api/webhooks/123456/abcdef"
        content = "Test digest message"

        with patch("app.services.delivery.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=204)

            result = DeliveryService.deliver_via_discord(webhook_url, content)

            assert result is True
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == webhook_url
            assert call_args[1]["json"]["content"] == content

    def test_deliver_via_discord_chunking(self):
        """Test Discord chunking for large content"""
        webhook_url = "https://discord.com/api/webhooks/123456/abcdef"
        # Create content > 1950 chars
        content = "\n".join(["Line " + str(i) for i in range(100)])

        with patch("app.services.delivery.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=204)

            result = DeliveryService.deliver_via_discord(webhook_url, content)

            assert result is True
            # Should be called multiple times due to chunking
            assert mock_post.call_count >= 1

    def test_deliver_via_discord_rate_limit(self):
        """Test Discord rate limit handling"""
        webhook_url = "https://discord.com/api/webhooks/123456/abcdef"
        content = "Test message"

        with patch("app.services.delivery.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=429, text="Rate limited")

            result = DeliveryService.deliver_via_discord(webhook_url, content)

            assert result is False

    def test_deliver_via_discord_invalid_webhook(self):
        """Test Discord invalid webhook URL"""
        webhook_url = "https://discord.com/api/webhooks/123456/abcdef"
        content = "Test message"

        with patch("app.services.delivery.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=404, text="Not found")

            result = DeliveryService.deliver_via_discord(webhook_url, content)

            assert result is False

    def test_deliver_via_discord_timeout(self):
        """Test Discord timeout handling"""
        webhook_url = "https://discord.com/api/webhooks/123456/abcdef"
        content = "Test message"

        with patch("app.services.delivery.requests.post") as mock_post:
            mock_post.side_effect = __import__("requests").Timeout()

            result = DeliveryService.deliver_via_discord(webhook_url, content)

            assert result is False

    def test_validate_discord_webhook_valid(self):
        """Test validating a valid Discord webhook"""
        webhook_url = "https://discord.com/api/webhooks/123456/abcdef"

        with patch("app.services.delivery.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=204)

            result = DeliveryService.validate_discord_webhook(webhook_url)

            assert result is True

    def test_validate_discord_webhook_invalid_url(self):
        """Test validating invalid Discord webhook URL format"""
        webhook_url = "https://example.com/webhook"

        result = DeliveryService.validate_discord_webhook(webhook_url)

        assert result is False

    def test_validate_discord_webhook_empty(self):
        """Test validating empty webhook URL"""
        result = DeliveryService.validate_discord_webhook("")

        assert result is False


class TestEmailDelivery:
    @patch.dict("os.environ", {"SENDGRID_API_KEY": "test-key", "SENDGRID_FROM_EMAIL": "digest@example.com"})
    def test_deliver_via_email_success(self):
        """Test successful email delivery"""
        email = "user@example.com"
        subject = "Daily Digest"
        html_content = "<h1>Digest</h1>"

        with patch("sendgrid.SendGridAPIClient") as mock_sg:
            mock_instance = MagicMock()
            mock_instance.send.return_value = MagicMock(status_code=202)
            mock_sg.return_value = mock_instance

            result = DeliveryService.deliver_via_email(email, subject, html_content)

            assert result is True
            mock_instance.send.assert_called_once()

    @patch.dict("os.environ", {"SENDGRID_API_KEY": "test-key"}, clear=True)
    def test_deliver_via_email_without_sender_fails(self):
        """A missing sender address must not fall back to a made-up default"""
        with patch("sendgrid.SendGridAPIClient") as mock_sg:
            result = DeliveryService.deliver_via_email("user@example.com", "Digest", "<p>x</p>")

        assert result is False
        mock_sg.assert_not_called()

    def test_deliver_via_email_no_api_key(self):
        """Test email delivery without API key"""
        email = "user@example.com"
        subject = "Daily Digest"
        html_content = "<h1>Digest</h1>"

        with patch.dict("os.environ", {}, clear=True):
            result = DeliveryService.deliver_via_email(email, subject, html_content)

            assert result is False

    def test_deliver_via_email_invalid_email(self):
        """Test email delivery with invalid email"""
        email = "invalid-email"
        subject = "Daily Digest"
        html_content = "<h1>Digest</h1>"

        result = DeliveryService.deliver_via_email(email, subject, html_content)

        # Should fail validation
        assert result is False

    def test_validate_email_valid(self):
        """Test email validation with valid email"""
        assert DeliveryService.validate_email("user@example.com") is True
        assert DeliveryService.validate_email("test.user+tag@example.co.uk") is True

    def test_validate_email_invalid(self):
        """Test email validation with invalid emails"""
        assert DeliveryService.validate_email("invalid") is False
        assert DeliveryService.validate_email("@example.com") is False
        assert DeliveryService.validate_email("user@") is False
        assert DeliveryService.validate_email("") is False

    def test_format_digest_for_email(self):
        """Test email formatting"""
        digest_content = "**Test Article**\nThis is a test digest"
        user_email = "user@example.com"

        html, text = DeliveryService.format_digest_for_email(digest_content, user_email, "Daily Digest")

        assert "Daily Digest" in html
        assert digest_content in html
        assert text == digest_content


class TestDeliveryAPI:
    def test_create_discord_channel_success(self, client, db: Session):
        """Test creating a Discord delivery channel"""
        # Setup
        user = User(email="delivery@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        schedule = Schedule(
            user_id=user.id, name="Test Schedule", cron_expression="0 6 * * *", next_run_at=datetime.now(UTC)
        )
        db.add(schedule)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "delivery@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        # Mock Discord webhook validation
        with patch("app.services.delivery.DeliveryService.validate_discord_webhook") as mock_validate:
            mock_validate.return_value = True

            response = client.post(
                f"/api/schedules/{schedule.id}/channels",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "type": "discord",
                    "config": {"webhook_url": "https://discord.com/api/webhooks/123456/abcdef"},
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "discord"
        assert data["schedule_id"] == schedule.id

    def test_create_email_channel_success(self, client, db: Session):
        """Test creating an email delivery channel"""
        # Setup
        user = User(email="emailchannel@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        schedule = Schedule(
            user_id=user.id, name="Test Schedule", cron_expression="0 6 * * *", next_run_at=datetime.now(UTC)
        )
        db.add(schedule)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "emailchannel@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.post(
            f"/api/schedules/{schedule.id}/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"type": "email", "config": {"email": "recipient@example.com"}},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "email"

    def test_create_channel_invalid_discord_url(self, client, db: Session):
        """Test creating channel with invalid Discord webhook"""
        user = User(email="invaliddiscord@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        schedule = Schedule(
            user_id=user.id, name="Test Schedule", cron_expression="0 6 * * *", next_run_at=datetime.now(UTC)
        )
        db.add(schedule)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "invaliddiscord@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.post(
            f"/api/schedules/{schedule.id}/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"type": "discord", "config": {"webhook_url": "https://example.com/webhook"}},
        )

        assert response.status_code == 400

    def test_list_channels(self, client, db: Session):
        """Test listing delivery channels"""
        user = User(email="listchannels@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        schedule = Schedule(
            user_id=user.id, name="Test Schedule", cron_expression="0 6 * * *", next_run_at=datetime.now(UTC)
        )
        db.add(schedule)
        db.commit()

        # Create channels
        channel1 = DeliveryChannel(
            schedule_id=schedule.id,
            type="discord",
            config=json.dumps({"webhook_url": "https://discord.com/api/webhooks/123/abc"}),
            is_enabled=True,
        )
        channel2 = DeliveryChannel(
            schedule_id=schedule.id,
            type="email",
            config=json.dumps({"email": "test@example.com"}),
            is_enabled=True,
        )
        db.add(channel1)
        db.add(channel2)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "listchannels@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.get(
            f"/api/schedules/{schedule.id}/channels", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_delete_channel(self, client, db: Session):
        """Test deleting a delivery channel"""
        user = User(email="deletechannel@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        schedule = Schedule(
            user_id=user.id, name="Test Schedule", cron_expression="0 6 * * *", next_run_at=datetime.now(UTC)
        )
        db.add(schedule)
        db.commit()

        channel = DeliveryChannel(
            schedule_id=schedule.id,
            type="discord",
            config=json.dumps({"webhook_url": "https://discord.com/api/webhooks/123/abc"}),
            is_enabled=True,
        )
        db.add(channel)
        db.commit()
        channel_id = channel.id

        response = client.post(
            "/api/auth/login", json={"email": "deletechannel@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.delete(
            f"/api/schedules/{schedule.id}/channels/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify deletion
        response = client.get(
            f"/api/schedules/{schedule.id}/channels", headers={"Authorization": f"Bearer {token}"}
        )
        assert len(response.json()) == 0

    def test_channel_requires_auth(self, client):
        """Test that channel endpoints require authentication"""
        response = client.get("/api/schedules/1/channels")
        assert response.status_code == 403

        response = client.post("/api/schedules/1/channels", json={"type": "discord", "config": {}})
        assert response.status_code == 403
