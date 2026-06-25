"""Shared test helpers for generating tokens and API Gateway events."""

import json
import time

import jwt

JWT_SECRET = "test-secret-key-for-unit-tests"


def generate_token(username, expired=False):
    """Generate a JWT token for testing.

    Args:
        username: The username to embed in the token.
        expired: If True, generate an already-expired token.

    Returns:
        A JWT token string.
    """
    now = int(time.time())
    if expired:
        payload = {
            "username": username,
            "exp": now - 3600,  # Expired 1 hour ago
            "iat": now - 7200,
        }
    else:
        payload = {
            "username": username,
            "exp": now + 86400,  # Expires in 24 hours
            "iat": now,
        }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def make_event(route_key, body=None, headers=None, query_params=None):
    """Create a mock API Gateway REST API proxy integration event.

    Args:
        route_key: The route key (e.g., "POST /auth/register").
            Parsed into httpMethod and resource for REST API format.
        body: Dict to serialize as JSON body, or None.
        headers: Dict of headers, or None.
        query_params: Dict of query string parameters, or None.

    Returns:
        A dict matching the API Gateway REST API proxy event format.
    """
    # Parse "METHOD /path" into httpMethod and resource
    parts = route_key.split(" ", 1)
    http_method = parts[0] if len(parts) > 0 else ""
    resource = parts[1] if len(parts) > 1 else ""

    event = {
        "httpMethod": http_method,
        "resource": resource,
    }
    if body is not None:
        event["body"] = json.dumps(body)
    if headers is not None:
        event["headers"] = headers
    else:
        event["headers"] = {}
    if query_params is not None:
        event["queryStringParameters"] = query_params
    return event
