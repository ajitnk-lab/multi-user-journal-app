import os
import json

import boto3
import jwt


class AuthError(Exception):
    """Custom exception for authentication errors."""

    def __init__(self, message, status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


_jwt_secret_cache = None


def get_jwt_secret():
    """Retrieve the JWT secret from AWS Systems Manager Parameter Store.

    Caches the secret for the lifetime of the Lambda execution context.
    """
    global _jwt_secret_cache
    if _jwt_secret_cache is not None:
        return _jwt_secret_cache

    parameter_name = os.environ.get("JWT_SECRET_PARAMETER", "/journal/jwt-secret")
    ssm = boto3.client("ssm")
    response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
    _jwt_secret_cache = response["Parameter"]["Value"]
    return _jwt_secret_cache


def verify_token(event):
    """Verify JWT token from the Authorization header.

    Args:
        event: API Gateway HTTP API v2 event

    Returns:
        str: The username extracted from the token

    Raises:
        AuthError: If token is missing, invalid, or expired
    """
    headers = event.get("headers", {})
    auth_header = headers.get("authorization", "")

    if not auth_header.startswith("Bearer "):
        raise AuthError("Missing or invalid authorization header")

    token = auth_header[7:]

    try:
        secret = get_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        username = payload.get("username")
        if not username:
            raise AuthError("Invalid token: missing username claim")
        return username
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")
