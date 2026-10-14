import pytest
from pydantic import ValidationError

from app.config import Settings


def test_health_check(client):
    """Health check returns status only, no configuration details"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "News Agent API" in response.json()["message"]


def test_api_docs(client):
    """Test API documentation is available"""
    response = client.get("/docs")
    assert response.status_code == 200
    assert (
        "openapi" in response.headers.get("content-type", "").lower()
        or "html" in response.headers.get("content-type", "").lower()
    )


class TestCors:
    def test_allowed_origin_is_echoed(self, client):
        response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_unknown_origin_is_rejected(self, client):
        response = client.get("/api/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in response.headers


class TestSettings:
    """Missing or placeholder secrets must fail at startup, not fall back silently"""

    def test_missing_secret_key_fails(self, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_missing_database_url_fails(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_short_secret_key_fails(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "too-short")
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_placeholder_secret_key_fails(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "your-secret-key-change-in-production-please")
        with pytest.raises(ValidationError):
            Settings(_env_file=None)
