import json
import time

import jwt
import pytest

from tests.helpers import JWT_SECRET
from utils.auth import verify_token, AuthError


class TestVerifyToken:
    """Tests for the verify_token utility function."""

    def test_verify_token_succeeds_with_valid_token(self, aws_mock):
        """verify_token returns the username for a valid, non-expired token."""
        token = jwt.encode(
            {
                "username": "validuser",
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
            },
            JWT_SECRET,
            algorithm="HS256",
        )
        event = {
            "headers": {"authorization": f"Bearer {token}"},
        }
        username = verify_token(event)
        assert username == "validuser"

    def test_verify_token_fails_with_expired_token(self, aws_mock):
        """verify_token raises AuthError for an expired token."""
        token = jwt.encode(
            {
                "username": "expireduser",
                "exp": int(time.time()) - 3600,
                "iat": int(time.time()) - 7200,
            },
            JWT_SECRET,
            algorithm="HS256",
        )
        event = {
            "headers": {"authorization": f"Bearer {token}"},
        }
        with pytest.raises(AuthError) as exc_info:
            verify_token(event)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.message.lower()

    def test_verify_token_fails_with_invalid_signature(self, aws_mock):
        """verify_token raises AuthError when the token is signed with a wrong secret."""
        token = jwt.encode(
            {
                "username": "baduser",
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
            },
            "wrong-secret-key",
            algorithm="HS256",
        )
        event = {
            "headers": {"authorization": f"Bearer {token}"},
        }
        with pytest.raises(AuthError) as exc_info:
            verify_token(event)
        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.message.lower() or "Invalid" in exc_info.value.message
