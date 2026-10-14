"""Tests for authentication endpoints"""

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User


class TestRegister:
    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post(
            "/api/auth/register", json={"email": "newuser@test.com", "password": "SecurePassword123"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["user_id"] > 0
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email"""
        # First registration
        client.post(
            "/api/auth/register", json={"email": "duplicate@test.com", "password": "SecurePassword123"}
        )

        # Second registration with same email
        response = client.post(
            "/api/auth/register", json={"email": "duplicate@test.com", "password": "DifferentPassword123"}
        )
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        response = client.post(
            "/api/auth/register", json={"email": "not-an-email", "password": "SecurePassword123"}
        )
        assert response.status_code == 422  # Validation error

    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        # No uppercase
        response = client.post(
            "/api/auth/register", json={"email": "test@test.com", "password": "weakpassword123"}
        )
        assert response.status_code == 422

        # No digit
        response = client.post(
            "/api/auth/register", json={"email": "test@test.com", "password": "WeakPassword"}
        )
        assert response.status_code == 422

    def test_register_short_password(self, client):
        """Test registration with short password"""
        response = client.post("/api/auth/register", json={"email": "test@test.com", "password": "Short1"})
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client, db: Session):
        """Test successful login"""
        # Create user
        user = User(email="login@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        # Login
        response = client.post(
            "/api/auth/login", json={"email": "login@test.com", "password": "SecurePassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "login@test.com"
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_email(self, client):
        """Test login with non-existent email"""
        response = client.post(
            "/api/auth/login", json={"email": "nonexistent@test.com", "password": "SecurePassword123"}
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_invalid_password(self, client, db: Session):
        """Test login with wrong password"""
        # Create user
        user = User(email="login2@test.com", password_hash=hash_password("SecurePassword123"))
        db.add(user)
        db.commit()

        # Login with wrong password
        response = client.post(
            "/api/auth/login", json={"email": "login2@test.com", "password": "WrongPassword123"}
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]


class TestGetCurrentUser:
    def test_get_current_user_success(self, client, db: Session):
        """Test getting current user info with valid token"""
        # Create user
        user = User(
            email="getuser@test.com", password_hash=hash_password("SecurePassword123"), email_verified=True
        )
        db.add(user)
        db.commit()

        # Login to get token
        login_response = client.post(
            "/api/auth/login", json={"email": "getuser@test.com", "password": "SecurePassword123"}
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = client.get("/api/auth/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "getuser@test.com"
        assert data["email_verified"] is True

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token"""
        response = client.get("/api/auth/users/me")
        assert response.status_code == 403

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        response = client.get("/api/auth/users/me", headers={"Authorization": "Bearer invalid_token_here"})
        assert response.status_code == 401


class TestVerifyEmail:
    def test_verify_email_invalid_token(self, client):
        """Test email verification with invalid token"""
        response = client.post("/api/auth/verify-email", json={"token": "invalid_token"})
        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]


class TestPasswordReset:
    def test_request_password_reset(self, client):
        """Test password reset request"""
        response = client.post("/api/auth/password-reset/request", json={"email": "nonexistent@test.com"})
        # Should return success regardless for security
        assert response.status_code == 200

    def test_confirm_password_reset_invalid_token(self, client):
        """Test password reset confirm with invalid token"""
        response = client.post(
            "/api/auth/password-reset/confirm",
            json={"token": "invalid_token", "new_password": "NewPassword123"},
        )
        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]


class TestChangePassword:
    def test_change_password_success(self, client, db: Session):
        """Test changing password for authenticated user"""
        # Create user
        user = User(email="changepass@test.com", password_hash=hash_password("OldPassword123"))
        db.add(user)
        db.commit()

        # Login
        login_response = client.post(
            "/api/auth/login", json={"email": "changepass@test.com", "password": "OldPassword123"}
        )
        token = login_response.json()["access_token"]

        # Change password
        response = client.post(
            "/api/auth/password-change",
            headers={"Authorization": f"Bearer {token}"},
            json={"old_password": "OldPassword123", "new_password": "NewPassword123"},
        )
        assert response.status_code == 200

        # Verify new password works
        login_response = client.post(
            "/api/auth/login", json={"email": "changepass@test.com", "password": "NewPassword123"}
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_old(self, client, db: Session):
        """Test changing password with wrong old password"""
        # Create user
        user = User(email="changepass2@test.com", password_hash=hash_password("OldPassword123"))
        db.add(user)
        db.commit()

        # Login
        login_response = client.post(
            "/api/auth/login", json={"email": "changepass2@test.com", "password": "OldPassword123"}
        )
        token = login_response.json()["access_token"]

        # Try to change with wrong old password
        response = client.post(
            "/api/auth/password-change",
            headers={"Authorization": f"Bearer {token}"},
            json={"old_password": "WrongPassword123", "new_password": "NewPassword123"},
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"]
