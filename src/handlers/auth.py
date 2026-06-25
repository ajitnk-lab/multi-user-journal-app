import json
import os
import re
import time

import boto3
import bcrypt
import jwt

from utils.auth import get_jwt_secret


def handler(event, context):
    """Lambda handler for authentication routes.

    Routes:
        POST /auth/register - Register a new user
        POST /auth/login - Login and get JWT token
    """
    try:
        http_method = event.get("httpMethod", "")
        resource = event.get("resource", "")

        if http_method == "POST" and resource == "/auth/register":
            return _register(event)
        elif http_method == "POST" and resource == "/auth/login":
            return _login(event)
        else:
            return _response(400, {"error": "Invalid route"})
    except Exception as e:
        return _response(500, {"error": "Internal server error"})


def _register(event):
    """Register a new user."""
    body = _parse_body(event)
    if body is None:
        return _response(400, {"error": "Invalid request body"})

    username = body.get("username", "")
    password = body.get("password", "")

    # Validate username: 3-20 characters, alphanumeric only
    if not re.match(r"^[a-zA-Z0-9]{3,20}$", username):
        return _response(400, {"error": "Username must be 3-20 alphanumeric characters"})

    # Validate password: minimum 8 characters
    if len(password) < 8:
        return _response(400, {"error": "Password must be at least 8 characters"})

    table_name = os.environ.get("USERS_TABLE_NAME", "users")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # Check user count (scan to count all users)
    scan_response = table.scan(Select="COUNT")
    user_count = scan_response.get("Count", 0)

    if user_count >= 10:
        return _response(400, {"error": "Maximum number of users reached"})

    # Hash password with bcrypt (12 salt rounds)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))

    # Store user in DynamoDB with atomic uniqueness check
    try:
        table.put_item(
            Item={
                "username": username,
                "password_hash": password_hash.decode("utf-8"),
                "created_at": int(time.time()),
            },
            ConditionExpression="attribute_not_exists(username)",
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _response(400, {"error": "Username already exists"})

    return _response(201, {"message": "User registered successfully"})


def _login(event):
    """Login a user and return JWT token."""
    body = _parse_body(event)
    if body is None:
        return _response(400, {"error": "Invalid request body"})

    username = body.get("username", "")
    password = body.get("password", "")

    if not username or not password:
        return _response(400, {"error": "Username and password are required"})

    table_name = os.environ.get("USERS_TABLE_NAME", "users")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # Retrieve user
    response = table.get_item(Key={"username": username})
    if "Item" not in response:
        return _response(401, {"error": "Invalid username or password"})

    user = response["Item"]
    stored_hash = user["password_hash"].encode("utf-8")

    # Verify password
    if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return _response(401, {"error": "Invalid username or password"})

    # Generate JWT token with 24h expiry
    secret = get_jwt_secret()
    token = jwt.encode(
        {
            "username": username,
            "exp": int(time.time()) + 86400,  # 24 hours
            "iat": int(time.time()),
        },
        secret,
        algorithm="HS256",
    )

    return _response(200, {"token": token})


def _parse_body(event):
    """Parse JSON body from event."""
    try:
        body = event.get("body", "")
        if isinstance(body, str):
            return json.loads(body)
        return body
    except (json.JSONDecodeError, TypeError):
        return None


def _response(status_code, body):
    """Create a standardized API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body),
    }
