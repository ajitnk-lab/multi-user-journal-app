import json

from tests.helpers import generate_token, make_event
from handlers.entries import handler as entries_handler
from handlers.search import handler as search_handler


class TestSearchEntries:
    """Tests for the GET /entries/search endpoint."""

    def test_search_returns_matching_entries_case_insensitive(self, aws_mock):
        """Search finds entries by case-insensitive substring match."""
        token = generate_token("searchuser")

        # Create entries with varied content
        contents = [
            "Beautiful sunny day at the park",
            "Rainy Monday morning",
            "Another SUNNY afternoon",
        ]
        for content in contents:
            event = make_event(
                "POST /entries",
                body={"content": content},
                headers={"authorization": f"Bearer {token}"},
            )
            entries_handler(event, None)

        # Search for "sunny" (case-insensitive)
        event = make_event(
            "GET /entries/search",
            headers={"authorization": f"Bearer {token}"},
            query_params={"q": "sunny"},
        )
        response = search_handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["entries"]) == 2

    def test_search_returns_empty_for_no_matches(self, aws_mock):
        """Search returns an empty list when no entries match the query."""
        token = generate_token("searchuser")

        # Create an entry
        event = make_event(
            "POST /entries",
            body={"content": "Just a regular day"},
            headers={"authorization": f"Bearer {token}"},
        )
        entries_handler(event, None)

        # Search for something that does not match
        event = make_event(
            "GET /entries/search",
            headers={"authorization": f"Bearer {token}"},
            query_params={"q": "xyz123nonexistent"},
        )
        response = search_handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["entries"] == []

    def test_search_fails_without_token(self, aws_mock):
        """Search fails with 401 when no authorization header is present."""
        event = make_event(
            "GET /entries/search",
            headers={},
            query_params={"q": "test"},
        )
        response = search_handler(event, None)
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "error" in body

    def test_search_fails_with_query_exceeding_100_chars(self, aws_mock):
        """Search fails when query exceeds 100 characters."""
        token = generate_token("searchuser")
        long_query = "a" * 101
        event = make_event(
            "GET /entries/search",
            headers={"authorization": f"Bearer {token}"},
            query_params={"q": long_query},
        )
        response = search_handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "100" in body["error"]

    def test_search_only_returns_current_user_entries(self, aws_mock):
        """Search returns only entries belonging to the authenticated user."""
        token_user1 = generate_token("user1")
        token_user2 = generate_token("user2")

        # User1 creates an entry with "secret"
        event = make_event(
            "POST /entries",
            body={"content": "This is user1 secret diary"},
            headers={"authorization": f"Bearer {token_user1}"},
        )
        entries_handler(event, None)

        # User2 creates an entry with "secret"
        event = make_event(
            "POST /entries",
            body={"content": "User2 also has a secret"},
            headers={"authorization": f"Bearer {token_user2}"},
        )
        entries_handler(event, None)

        # User1 searches for "secret" - should only see their own entry
        event = make_event(
            "GET /entries/search",
            headers={"authorization": f"Bearer {token_user1}"},
            query_params={"q": "secret"},
        )
        response = search_handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["entries"]) == 1
        assert "user1" in body["entries"][0]["content"]
