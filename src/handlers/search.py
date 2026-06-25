import json
import os
from decimal import Decimal

import boto3

from utils.auth import verify_token, AuthError


def handler(event, context):
    """Lambda handler for search routes.

    Routes:
        GET /entries/search - Search entries by content substring
    """
    try:
        http_method = event.get("httpMethod", "")
        resource = event.get("resource", "")

        if http_method == "GET" and resource == "/entries/search":
            return _search_entries(event)
        else:
            return _response(400, {"error": "Invalid route"})
    except AuthError as e:
        return _response(e.status_code, {"error": e.message})
    except Exception as e:
        return _response(500, {"error": "Internal server error"})


def _search_entries(event):
    """Search entries by case-insensitive substring match on content."""
    username = verify_token(event)

    # Get query parameter
    query_params = event.get("queryStringParameters") or {}
    query = query_params.get("q", "")

    if not query:
        return _response(400, {"error": "Search query parameter 'q' is required"})

    if len(query) > 100:
        return _response(400, {"error": "Search query must not exceed 100 characters"})

    table_name = os.environ.get("ENTRIES_TABLE_NAME", "journal_entries")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # Query entries by username with pagination to handle results beyond 1 MB
    all_items = []
    query_kwargs = {
        "KeyConditionExpression": boto3.dynamodb.conditions.Key("username").eq(username),
        "ScanIndexForward": False,
    }

    while True:
        response = table.query(**query_kwargs)
        all_items.extend(response.get("Items", []))

        # Check if there are more pages
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        query_kwargs["ExclusiveStartKey"] = last_key

    # Filter by case-insensitive substring match on content
    query_lower = query.lower()
    entries = [
        {
            "entry_id": item["entry_id"],
            "content": item["content"],
            "created_at": item.get("created_at"),
        }
        for item in all_items
        if query_lower in item.get("content", "").lower()
    ]

    return _response(200, {"entries": entries})


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
