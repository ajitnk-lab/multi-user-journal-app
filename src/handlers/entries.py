import json
import os
import time
from decimal import Decimal

import boto3
from ulid import ULID

from utils.auth import verify_token, AuthError


def handler(event, context):
    """Lambda handler for journal entry routes.

    Routes:
        POST /entries - Create a new journal entry
        GET /entries - List all entries for the authenticated user
    """
    try:
        http_method = event.get("httpMethod", "")
        resource = event.get("resource", "")

        if http_method == "POST" and resource == "/entries":
            return _create_entry(event)
        elif http_method == "GET" and resource == "/entries":
            return _list_entries(event)
        else:
            return _response(400, {"error": "Invalid route"})
    except AuthError as e:
        return _response(e.status_code, {"error": e.message})
    except Exception as e:
        return _response(500, {"error": "Internal server error"})


def _create_entry(event):
    """Create a new journal entry."""
    username = verify_token(event)

    body = _parse_body(event)
    if body is None:
        return _response(400, {"error": "Invalid request body"})

    content = body.get("content", "")

    if not content:
        return _response(400, {"error": "Content is required"})

    if len(content) > 10000:
        return _response(400, {"error": "Content must not exceed 10000 characters"})

    table_name = os.environ.get("ENTRIES_TABLE_NAME", "journal_entries")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # Generate ULID for time-sortable entry ID
    entry_id = str(ULID())
    created_at = int(time.time())

    item = {
        "username": username,
        "entry_id": entry_id,
        "content": content,
        "created_at": created_at,
    }

    table.put_item(Item=item)

    return _response(201, {
        "entry_id": entry_id,
        "content": content,
        "created_at": created_at,
    })


def _list_entries(event):
    """List all entries for the authenticated user, sorted newest first."""
    username = verify_token(event)

    table_name = os.environ.get("ENTRIES_TABLE_NAME", "journal_entries")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # Query entries by username, sorted by entry_id (ULID) descending
    # Handle pagination to retrieve all results beyond DynamoDB 1 MB limit
    all_items = []
    query_kwargs = {
        "KeyConditionExpression": boto3.dynamodb.conditions.Key("username").eq(username),
        "ScanIndexForward": False,  # Sort descending (newest first)
    }

    while True:
        response = table.query(**query_kwargs)
        all_items.extend(response.get("Items", []))

        # Check if there are more pages
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        query_kwargs["ExclusiveStartKey"] = last_key

    entries = [
        {
            "entry_id": item["entry_id"],
            "content": item["content"],
            "created_at": item.get("created_at"),
        }
        for item in all_items
    ]

    return _response(200, {"entries": entries})


def _parse_body(event):
    """Parse JSON body from event."""
    try:
        body = event.get("body", "")
        if isinstance(body, str):
            return json.loads(body)
        return body
    except (json.JSONDecodeError, TypeError):
        return None


class _DecimalEncoder(json.JSONEncoder):
    """JSON encoder that converts Decimal values to int or float."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


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
        "body": json.dumps(body, cls=_DecimalEncoder),
    }
