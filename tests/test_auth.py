import json

import bcrypt

from tests.helpers import generate_token, make_event, JWT_SECRET
from handlers.auth import handler


class TestRegistration:
    """Tests for the POST /auth/register endpoint."""

    def test_successful_registration(self, aws_mock):
        """Registration succeeds with valid username and password."""
        event = make_event(
            "POST /auth/register",
            body={"username": "testuser", "password": "securepass123"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["message"] == "User registered successfully"

        # Verify user was stored in DynamoDB
        item = aws_mock["users_table"].get_item(Key={"username": "testuser"})
        assert "Item" in item
        assert item["Item"]["username"] == "testuser"

    def test_registration_fails_username_already_exists(self, aws_mock):
        """Registration fails when the username is already taken."""
        # Register first user
        event = make_event(
            "POST /auth/register",
            body={"username": "existinguser", "password": "securepass123"},
        )
        handler(event, None)

        # Try to register again with same username
        response = handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "already exists" in body["error"]

    def test_registration_fails_when_10_users_exist(self, aws_mock):
        """Registration fails when 10 users already exist (max user limit)."""
        # Register 10 users
        for i in range(10):
            event = make_event(
                "POST /auth/register",
                body={"username": f"user{i:03d}", "password": "securepass123"},
            )
            response = handler(event, None)
            assert response["statusCode"] == 201, f"Failed to register user{i:03d}"

        # 11th user should be rejected
        event = make_event(
            "POST /auth/register",
            body={"username": "user010", "password": "securepass123"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Maximum number of users" in body["error"]

    def test_registration_fails_with_invalid_username_format(self, aws_mock):
        """Registration fails when username contains invalid characters."""
        invalid_usernames = [
            "ab",  # Too short (< 3 chars)
            "a" * 21,  # Too long (> 20 chars)
            "user name",  # Contains space
            "user@name",  # Contains special char
            "user-name",  # Contains hyphen
        ]
        for username in invalid_usernames:
            event = make_event(
                "POST /auth/register",
                body={"username": username, "password": "securepass123"},
            )
            response = handler(event, None)
            assert response["statusCode"] == 400, f"Username '{username}' should be rejected"
            body = json.loads(response["body"])
            assert "alphanumeric" in body["error"]

    def test_registration_fails_with_short_password(self, aws_mock):
        """Registration fails when password is shorter than 8 characters."""
        event = make_event(
            "POST /auth/register",
            body={"username": "testuser", "password": "short"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "at least 8 characters" in body["error"]


class TestLogin:
    """Tests for the POST /auth/login endpoint."""

    def test_successful_login_returns_jwt(self, aws_mock):
        """Login succeeds with correct credentials and returns a JWT token."""
        # Register a user first
        event = make_event(
            "POST /auth/register",
            body={"username": "loginuser", "password": "securepass123"},
        )
        handler(event, None)

        # Login with the same credentials
        event = make_event(
            "POST /auth/login",
            body={"username": "loginuser", "password": "securepass123"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "token" in body
        assert isinstance(body["token"], str)
        assert len(body["token"]) > 0

    def test_login_fails_with_wrong_password(self, aws_mock):
        """Login fails when the password is incorrect."""
        # Register a user
        event = make_event(
            "POST /auth/register",
            body={"username": "loginuser", "password": "securepass123"},
        )
        handler(event, None)

        # Login with wrong password
        event = make_event(
            "POST /auth/login",
            body={"username": "loginuser", "password": "wrongpassword"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "Invalid username or password" in body["error"]

    def test_login_fails_with_nonexistent_user(self, aws_mock):
        """Login fails when the user does not exist."""
        event = make_event(
            "POST /auth/login",
            body={"username": "nouser", "password": "anypassword"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "Invalid username or password" in body["error"]
