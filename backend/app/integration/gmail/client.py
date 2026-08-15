from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.integration.gmail.token_store import load_token
from app.core.config import settings
import base64
from pathlib import Path


class GmailClient:
    """Client for interacting with the Gmail API."""

    def __init__(self) -> None:
        token_data = load_token()

        if not token_data:
            raise RuntimeError(
                "Gmail credentials not found. "
                "Authenticate Gmail first."
            )

        self.credentials = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get(
                "token_uri",
                "https://oauth2.googleapis.com/token",
            ),
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=token_data.get(
                "scopes",
                settings.gmail_scopes.split(","),
            ),
        )

        self.service = build(
            "gmail",
            "v1",
            credentials=self.credentials,
        )

    def list_messages(self, max_results: int = 10) -> list[dict]:
        """Return basic information about recent Gmail messages."""

        response = (
            self.service.users()
            .messages()
            .list(
                userId="me",
                maxResults=max_results,
            )
            .execute()
        )

        messages = response.get("messages", [])

        results = []

        for message in messages:
            message_data = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=message["id"],
                    format="metadata",
                    metadataHeaders=[
                        "Subject",
                        "From",
                        "Date",
                    ],
                )
                .execute()
            )

            headers = {
                header["name"].lower(): header["value"]
                for header in message_data
                .get("payload", {})
                .get("headers", [])
            }

            results.append(
                {
                    "id": message_data["id"],
                    "thread_id": message_data.get("threadId"),
                    "subject": headers.get("subject", ""),
                    "sender": headers.get("from", ""),
                    "date": headers.get("date", ""),
                }
            )

        return results

    def list_attachments(self, max_results: int = 10) -> list[dict]:
        """Find attachments in recent Gmail messages."""

        response = (
            self.service.users()
            .messages()
            .list(
                userId="me",
                maxResults=max_results,
            )
            .execute()
        )

        messages = response.get("messages", [])
        attachments = []

        for message in messages:
            message_id = message["id"]

            message_data = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="full",
                )
                .execute()
            )

            payload = message_data.get("payload", {})

            self._extract_attachments(
                payload=payload,
                message_id=message_id,
                attachments=attachments,
            )

        return attachments

    def _extract_attachments(
        self,
        payload: dict,
        message_id: str,
        attachments: list[dict],
    ) -> None:
        """Recursively find attachments inside a Gmail message."""

        filename = payload.get("filename", "")
        body = payload.get("body", {})

        if filename and body.get("attachmentId"):
            attachments.append(
                {
                    "message_id": message_id,
                    "filename": filename,
                    "mime_type": payload.get("mimeType"),
                    "attachment_id": body["attachmentId"],
                }
            )

        for part in payload.get("parts", []):
            self._extract_attachments(
                payload=part,
                message_id=message_id,
                attachments=attachments,
            )

    def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        filename: str,
        output_dir: str = "uploads/resumes",
    ) -> str:
        """Download a Gmail attachment and save it locally."""

        attachment = (
            self.service.users()
            .messages()
            .attachments()
            .get(
                userId="me",
                messageId=message_id,
                id=attachment_id,
            )
            .execute()
        )

        data = attachment.get("data")

        if not data:
            raise ValueError("Attachment contains no data")

        file_data = base64.urlsafe_b64decode(data)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / filename

        with open(file_path, "wb") as file:
            file.write(file_data)

        return str(file_path)

