"""Test Gmail OAuth PKCE flow after endpoint alignment and origin fix."""
import pytest
from fastapi.testclient import TestClient
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from httplib2 import Response

from app.api.v1.endpoints.gmail import get_gmail_service
from app.main import app
from app.services.gmail_ingestion import GmailIngestionService


client = TestClient(app)


def test_gmail_status_endpoint():
    """Test Gmail status endpoint exists and returns configured status."""
    response = client.get("/api/v1/gmail/status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "connected" in data


def test_gmail_auth_url_endpoint():
    """Test Gmail auth-url endpoint generates OAuth URL with PKCE."""
    response = client.get("/api/v1/gmail/auth-url")
    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "state" in data
    assert "accounts.google.com" in data["auth_url"]
    assert "code_challenge" in data["auth_url"]
    assert "code_challenge_method=S256" in data["auth_url"]


def test_gmail_callback_endpoint_get():
    """Test Gmail callback endpoint accepts GET requests."""
    response = client.get(
        "/api/v1/gmail/callback",
        params={"code": "test_code", "state": "test_state"}
    )
    # Should return HTML response even with invalid code
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_gmail_callback_uses_frontend_origin():
    """Test callback HTML uses configured frontend origin, not backend origin."""
    response = client.get(
        "/api/v1/gmail/callback",
        params={"code": "test_code", "state": "test_state"}
    )
    assert response.status_code == 200
    html = response.text
    # Should use frontend origin from config, not window.location.origin
    assert "http://localhost:5173" in html
    # Should NOT use backend origin or window.location.origin
    assert "window.location.origin" not in html
    assert "http://localhost:8000" not in html


def test_gmail_callback_notifies_opener_after_credentials_are_stored():
    events = []

    class Service:
        def exchange_code_for_token(self, code, state):
            events.append(("stored", code, state))

    app.dependency_overrides[get_gmail_service] = lambda: Service()
    try:
        response = client.get(
            "/api/v1/gmail/callback",
            params={"code": "oauth-code", "state": "oauth-state"},
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)

    assert response.status_code == 200
    assert events == [("stored", "oauth-code", "oauth-state")]
    assert '"type": "gmail_oauth_callback"' in response.text
    assert '"success": true' in response.text
    assert '"state": "oauth-state"' in response.text
    assert "window.opener.postMessage" in response.text


def test_gmail_callback_reports_google_authorization_denial():
    class Service:
        def cancel_auth(self, state):
            return state == "oauth-state"

    app.dependency_overrides[get_gmail_service] = lambda: Service()
    try:
        response = client.get(
            "/api/v1/gmail/callback",
            params={"error": "access_denied", "state": "oauth-state"},
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)

    assert response.status_code == 200
    assert '"success": false' in response.text
    assert "Google authorization was denied." in response.text


def test_gmail_status_uses_credentials_for_requested_state():
    class Service:
        def is_configured(self):
            return True

        def is_connected(self, state=None):
            return state == "connected-state"

    app.dependency_overrides[get_gmail_service] = lambda: Service()
    try:
        connected = client.get(
            "/api/v1/gmail/status", params={"state": "connected-state"}
        )
        disconnected = client.get(
            "/api/v1/gmail/status", params={"state": "unknown-state"}
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)

    assert connected.json()["connected"] is True
    assert disconnected.json()["connected"] is False


def test_gmail_service_connection_status_tracks_stored_credentials(monkeypatch):
    service = GmailIngestionService()
    monkeypatch.setattr(
        service,
        "_tokens",
        {"connected-state": Credentials(token="access-token")},
    )

    assert service.is_connected()
    assert service.is_connected("connected-state")
    assert not service.is_connected("unknown-state")


def test_gmail_no_login_endpoint():
    """Verify /gmail/login endpoint does not exist (404)."""
    response = client.get("/api/v1/gmail/login")
    assert response.status_code == 404


def test_gmail_search_endpoint():
    """Test Gmail search endpoint requires POST and state parameter."""
    response = client.post(
        "/api/v1/gmail/search",
        params={"state": "test_state"},
        json={"query": "resume", "max_results": 10}
    )
    # Should fail without valid credentials but endpoint exists
    assert response.status_code in [401, 400]


def test_gmail_search_scans_pages_and_returns_supported_attachment_metadata(monkeypatch):
    list_calls = []
    get_calls = []

    def message_payload(subject, sender, parts):
        return {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": subject},
                    {"name": "From", "value": sender},
                    {"name": "Date", "value": "Mon, 01 Jan 2024 00:00:00 +0000"},
                ],
                "parts": parts,
            }
        }

    def attachment(filename, mime_type, attachment_id):
        return {
            "filename": filename,
            "mimeType": mime_type,
            "body": {"attachmentId": attachment_id, "size": 123},
        }

    messages_by_id = {
        "message-1": message_payload(
            "Application",
            "sender@example.com",
            [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        attachment("resume.PDF", "application/pdf", "attach-pdf"),
                        attachment("notes.txt", "text/plain", "attach-txt"),
                    ],
                }
            ],
        ),
        "message-2": message_payload(
            "No resume keywords",
            "other@example.com",
            [
                attachment(
                    "profile.docx",
                    "application/octet-stream",
                    "attach-docx",
                ),
                attachment("cv.doc", "application/msword", "attach-doc"),
            ],
        ),
    }

    class Request:
        def __init__(self, response):
            self.response = response

        def execute(self):
            return self.response

    class Messages:
        def list(self, **kwargs):
            list_calls.append(kwargs)
            if kwargs.get("pageToken") == "next-page":
                return Request({"messages": [{"id": "message-2"}]})
            return Request(
                {
                    "messages": [{"id": "message-1"}],
                    "nextPageToken": "next-page",
                }
            )

        def get(self, **kwargs):
            get_calls.append(kwargs)
            return Request(messages_by_id[kwargs["id"]])

    class Users:
        def messages(self):
            return Messages()

    class GmailApi:
        def users(self):
            return Users()

    monkeypatch.setattr(
        "app.services.gmail_ingestion.build",
        lambda *args, **kwargs: GmailApi(),
    )
    service = GmailIngestionService()

    results = service.search_emails(
        Credentials(token="test-token"),
        query="resume OR cv",
        max_results=2,
    )

    assert len(list_calls) == 2
    assert "filename:pdf" in list_calls[0]["q"]
    assert "filename:docx" in list_calls[0]["q"]
    assert "filename:doc" in list_calls[0]["q"]
    assert "resume OR cv" in list_calls[0]["q"]
    assert list_calls[0]["maxResults"] == 2
    assert list_calls[1]["pageToken"] == "next-page"
    assert list_calls[1]["maxResults"] == 1
    assert all(call["format"] == "full" for call in get_calls)
    assert [item["filename"] for item in results] == [
        "resume.PDF",
        "profile.docx",
        "cv.doc",
    ]
    assert {
        key: value for key, value in results[0].items() if not key.startswith("_")
    } == {
        "message_id": "message-1",
        "attachment_id": "attach-pdf",
        "filename": "resume.PDF",
        "size": 123,
        "mime_type": "application/pdf",
        "subject": "Application",
        "sender": "sender@example.com",
        "date": "Mon, 01 Jan 2024 00:00:00 +0000",
    }


def test_gmail_search_endpoint_returns_empty_list_when_no_messages_match():
    class Service:
        def get_credentials(self, state):
            return Credentials(token="test-token")

        def search_emails(self, credentials, query, max_results):
            return []

        async def classify_attachments(self, credentials, attachments):
            return attachments

    app.dependency_overrides[get_gmail_service] = lambda: Service()
    try:
        response = client.post(
            "/api/v1/gmail/search",
            params={"state": "test-state"},
            json={"query": "resume", "max_results": 10},
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)

    assert response.status_code == 200
    assert response.json() == []


def test_gmail_search_endpoint_returns_frontend_attachment_fields():
    attachment = {
        "message_id": "message-1",
        "attachment_id": "attachment-1",
        "filename": "resume.pdf",
        "size": 123,
        "mime_type": "application/pdf",
        "subject": "Application",
        "sender": "sender@example.com",
        "date": "Mon, 01 Jan 2024 00:00:00 +0000",
    }

    class Service:
        def get_credentials(self, state):
            return Credentials(token="test-token")

        def search_emails(self, credentials, query, max_results):
            return [attachment]

        async def classify_attachments(self, credentials, attachments):
            return [
                {
                    **item,
                    "classification": "RESUME",
                    "confidence": 0.9,
                    "classification_reason": "Resume structure detected.",
                    "content_hash": "test-hash",
                }
                for item in attachments
            ]

    app.dependency_overrides[get_gmail_service] = lambda: Service()
    try:
        response = client.post(
            "/api/v1/gmail/search",
            params={"state": "test-state"},
            json={"query": "resume", "max_results": 10},
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)

    assert response.status_code == 200
    assert response.json() == [
        {
            **attachment,
            "classification": "RESUME",
            "confidence": 0.9,
            "classification_reason": "Resume structure detected.",
            "content_hash": "test-hash",
        }
    ]


@pytest.mark.parametrize(
    ("api_status", "expected_status"),
    [(401, 401), (403, 403), (503, 502)],
)
def test_gmail_search_endpoint_distinguishes_gmail_api_errors(
    api_status, expected_status
):
    class Service:
        def get_credentials(self, state):
            return Credentials(token="test-token")

        def search_emails(self, credentials, query, max_results):
            raise HttpError(
                Response({"status": str(api_status)}),
                b"private provider response",
            )

        async def classify_attachments(self, credentials, attachments):
            return attachments

    app.dependency_overrides[get_gmail_service] = lambda: Service()
    try:
        response = client.post(
            "/api/v1/gmail/search",
            params={"state": "test-state"},
            json={"query": "resume", "max_results": 10},
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)

    assert response.status_code == expected_status
    assert "private provider response" not in response.text
    if api_status == 503:
        assert response.json()["detail"] == "Gmail API search failed. Please try again."


def test_gmail_import_endpoint():
    """Test Gmail import endpoint requires POST and state parameter."""
    response = client.post(
        "/api/v1/gmail/import",
        params={"state": "test_state"},
        json={"attachments": []}
    )
    # Should fail without valid credentials but endpoint exists
    assert response.status_code in [401, 400]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
