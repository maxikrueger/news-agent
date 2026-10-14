"""Tests for source management endpoints"""

from unittest.mock import patch

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import Source, User
from app.schemas.source import FeedTestResponse


class TestSourceCRUD:
    @patch("app.services.source.SourceService.test_feed")
    def test_create_source_success(self, mock_test_feed, client, db: Session):
        """Test successful source creation"""
        # Mock the feed validation
        mock_test_feed.return_value = FeedTestResponse(valid=True, title="TechCrunch", entries=10)

        # Create user and login
        user = User(email="sourcetest@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "sourcetest@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        # Create source
        response = client.post(
            "/api/sources",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "TechCrunch",
                "url": "https://feeds.techcrunch.com/techcrunch/startups",
                "category": "Tech",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "TechCrunch"
        assert data["url"] == "https://feeds.techcrunch.com/techcrunch/startups"
        assert data["category"] == "Tech"
        assert data["id"] > 0

    def test_create_source_no_auth(self, client):
        """Test source creation without authentication"""
        response = client.post(
            "/api/sources",
            json={
                "name": "TechCrunch",
                "url": "https://feeds.techcrunch.com/techcrunch/startups",
                "category": "Tech",
            },
        )
        assert response.status_code == 403

    def test_create_source_invalid_url(self, client, db: Session):
        """Test source creation with invalid URL"""
        user = User(email="sourcetest2@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "sourcetest2@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.post(
            "/api/sources",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Invalid", "url": "not-a-valid-url", "category": "Tech"},
        )
        assert response.status_code == 422

    def test_create_source_invalid_category(self, client, db: Session):
        """Test source creation with invalid category"""
        user = User(email="sourcetest3@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "sourcetest3@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.post(
            "/api/sources",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Test",
                "url": "https://feeds.techcrunch.com/techcrunch/startups",
                "category": "InvalidCategory",
            },
        )
        assert response.status_code == 422

    def test_get_sources_list(self, client, db: Session):
        """Test listing user's sources"""
        user = User(email="listtest@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        # Add some sources
        source1 = Source(
            user_id=user.id, name="Source1", url="https://example.com/feed1.rss", category="Tech"
        )
        source2 = Source(
            user_id=user.id, name="Source2", url="https://example.com/feed2.rss", category="News"
        )
        db.add(source1)
        db.add(source2)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "listtest@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.get("/api/sources", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Source1"
        assert data[1]["name"] == "Source2"

    def test_get_source_detail(self, client, db: Session):
        """Test getting source details"""
        user = User(email="detailtest@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        source = Source(user_id=user.id, name="MySource", url="https://example.com/feed.rss")
        db.add(source)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "detailtest@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.get(f"/api/sources/{source.id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == source.id
        assert data["name"] == "MySource"

    def test_get_source_not_owned(self, client, db: Session):
        """Test getting source not owned by user"""
        user1 = User(email="user1@test.com", password_hash=hash_password("SecurePassword123"))
        user2 = User(email="user2@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user1)
        db.add(user2)
        db.commit()

        source = Source(user_id=user1.id, name="User1Source", url="https://example.com/feed.rss")
        db.add(source)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "user2@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.get(f"/api/sources/{source.id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 404

    def test_update_source(self, client, db: Session):
        """Test updating a source"""
        user = User(email="updatetest@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        source = Source(user_id=user.id, name="OldName", url="https://example.com/feed.rss", category="Tech")
        db.add(source)
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "updatetest@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.put(
            f"/api/sources/{source.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "NewName", "category": "News"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NewName"
        assert data["category"] == "News"

    def test_delete_source(self, client, db: Session):
        """Test deleting a source"""
        user = User(email="deletetest@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        source = Source(user_id=user.id, name="ToDelete", url="https://example.com/feed.rss")
        db.add(source)
        db.commit()
        source_id = source.id

        response = client.post(
            "/api/auth/login", json={"email": "deletetest@test.com", "password": "SecurePassword123"}
        )
        token = response.json()["access_token"]

        response = client.delete(f"/api/sources/{source_id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f"/api/sources/{source_id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 404


class TestRSSFeedValidation:
    def test_categories_endpoint(self, client):
        """Test getting available categories"""
        response = client.get("/api/sources/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "Tech" in data["categories"]
        assert "Business" in data["categories"]
        assert "News" in data["categories"]

    def test_feed_test_valid_rss(self, authenticated_client):
        """Test validating a valid RSS feed"""
        response = authenticated_client.post(
            "/api/sources/test", json={"url": "https://feeds.techcrunch.com/techcrunch/startups"}
        )
        assert response.status_code == 200
        data = response.json()
        # May or may not be valid depending on network, but response format should be correct
        assert "valid" in data
        assert "entries" in data
        assert isinstance(data["entries"], int)

    def test_feed_test_invalid_url(self, authenticated_client):
        """Test validating an invalid URL"""
        response = authenticated_client.post(
            "/api/sources/test", json={"url": "https://invalid-domain-that-does-not-exist-12345.xyz/feed"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "error" in data

    def test_feed_test_malformed_url(self, authenticated_client):
        """Test validating a malformed URL"""
        response = authenticated_client.post("/api/sources/test", json={"url": "not-a-valid-url"})
        assert response.status_code == 422


class TestSourceAuthorization:
    def test_list_only_own_sources(self, client, db: Session):
        """Test that users only see their own sources"""
        user1 = User(email="auth1@test.com", password_hash=hash_password("SecurePassword123"))
        user2 = User(email="auth2@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user1)
        db.add(user2)
        db.commit()

        # User1 has 2 sources
        source1 = Source(user_id=user1.id, name="User1Source1", url="https://example.com/feed1.rss")
        source2 = Source(user_id=user1.id, name="User1Source2", url="https://example.com/feed2.rss")
        # User2 has 1 source
        source3 = Source(user_id=user2.id, name="User2Source1", url="https://example.com/feed3.rss")
        db.add(source1)
        db.add(source2)
        db.add(source3)
        db.commit()

        # Login as User1
        response = client.post(
            "/api/auth/login", json={"email": "auth1@test.com", "password": "SecurePassword123"}
        )
        token1 = response.json()["access_token"]

        # User1 should see only 2 sources
        response = client.get("/api/sources", headers={"Authorization": f"Bearer {token1}"})
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Login as User2
        response = client.post(
            "/api/auth/login", json={"email": "auth2@test.com", "password": "SecurePassword123"}
        )
        token2 = response.json()["access_token"]

        # User2 should see only 1 source
        response = client.get("/api/sources", headers={"Authorization": f"Bearer {token2}"})
        assert response.status_code == 200
        assert len(response.json()) == 1
