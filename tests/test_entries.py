import json

from tests.helpers import generate_token, make_event
from handlers.entries import handler


class TestCreateEntry:
    """Tests for the POST /entries endpoint."""

    def test_create_entry_with_valid_token(self, aws_mock):
        """Creating an entry succeeds with a valid token and content."""
        token = generate_token("testuser")
        event = make_event(
            "POST /entries",
            body={"content": "Today was a great day!"},
            headers={"authorization": f"Bearer {token}"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert "entry_id" in body
        assert body["content"] == "Today was a great day!"
        assert "created_at" in body

    def test_create_entry_fails_without_token(self, aws_mock):
        """Creating an entry fails with 401 when no authorization header is present."""
        event = make_event(
            "POST /entries",
            body={"content": "Some content"},
            headers={},
        )
        response = handler(event, None)
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "error" in body

    def test_create_entry_fails_with_expired_token(self, aws_mock):
        """Creating an entry fails with 401 when the token is expired."""
        token = generate_token("testuser", expired=True)
        event = make_event(
            "POST /entries",
            body={"content": "Some content"},
            headers={"authorization": f"Bearer {token}"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "expired" in body["error"].lower() or "error" in body

    def test_create_entry_fails_with_content_exceeding_limit(self, aws_mock):
        """Creating an entry fails when content exceeds 10000 characters."""
        token = generate_token("testuser")
        long_content = "x" * 10001
        event = make_event(
            "POST /entries",
            body={"content": long_content},
            headers={"authorization": f"Bearer {token}"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "10000" in body["error"]


class TestListEntries:
    """Tests for the GET /entries endpoint."""

    def test_list_entries_returns_user_entries_sorted_newest_first(self, aws_mock):
        """Listing entries returns only the authenticated user's entries, newest first."""
        token = generate_token("testuser")

        # Create multiple entries
        entries_content = ["First entry", "Second entry", "Third entry"]
        for content in entries_content:
            event = make_event(
                "POST /entries",
                body={"content": content},
                headers={"authorization": f"Bearer {token}"},
            )
            handler(event, None)

        # List entries
        event = make_event(
            "GET /entries",
            headers={"authorization": f"Bearer {token}"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["entries"]) == 3

        # ULID-based entry_ids are time-sortable; ScanIndexForward=False means descending
        entry_ids = [e["entry_id"] for e in body["entries"]]
        assert entry_ids == sorted(entry_ids, reverse=True)

    def test_list_entries_returns_empty_for_user_with_no_entries(self, aws_mock):
        """Listing entries returns an empty list for a user who has no entries."""
        token = generate_token("emptyuser")
        event = make_event(
            "GET /entries",
            headers={"authorization": f"Bearer {token}"},
        )
        response = handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["entries"] == []
