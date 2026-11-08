import asyncio
import json
import hashlib
import logging
import re
import secrets
from typing import Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.schemas.gmail import GmailAttachment
from app.services.pdf_extraction import PDFExtractionService
from app.services.project_extraction import ProjectExtractionService
from app.services.resume_upload import ResumeUploadService
from app.services.resume_parser_service import ResumeParserService

logger = logging.getLogger(__name__)

SUPPORTED_ATTACHMENT_QUERY = (
    "has:attachment {filename:pdf filename:docx filename:doc}"
)
RESUME_CONTEXT_PATTERN = re.compile(
    r"\b(resume|curriculum vitae|cv|candidate|applying for|job application)\b",
    re.IGNORECASE,
)
NON_RESUME_PATTERN = re.compile(
    r"\b(infographic|brochure|newsletter|event flyer|scholarship application|"
    r"course catalog|product catalog|invoice|menu)\b",
    re.IGNORECASE,
)
MIN_CLASSIFICATION_TEXT_LENGTH = 100


class GmailIngestionService:
    """Service for Gmail OAuth and resume attachment ingestion."""

    # In-memory token storage (production should use database)
    _tokens: dict[str, Credentials] = {}
    _code_verifiers: dict[str, str] = {}

    def __init__(self) -> None:
        self.credentials_configured = bool(
            settings.google_client_id and settings.google_client_secret
        )
        self._attachment_classifications: dict[str, dict[str, Any]] = {}
        self._document_signals_by_hash: dict[str, dict[str, Any]] = {}
        self._document_classifications_by_hash: dict[str, dict[str, Any]] = {}
        self._llm_available: bool | None = None

    def get_auth_url(self) -> tuple[str, str]:
        """Generate OAuth authorization URL and state token."""
        if not self.credentials_configured:
            raise ValueError(
                "Google OAuth credentials not configured. "
                "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
            )

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=[settings.gmail_scopes],
            redirect_uri=settings.google_redirect_uri,
        )

        state = secrets.token_urlsafe(16)
        flow.redirect_uri = settings.google_redirect_uri

        auth_url, returned_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            code_challenge_method="S256",
        )

        if not flow.code_verifier:
            raise ValueError("OAuth PKCE code verifier was not generated")

        self._code_verifiers[returned_state] = flow.code_verifier

        return auth_url, returned_state

    def exchange_code_for_token(self, code: str, state: str) -> None:
        """Exchange OAuth authorization code for access token."""
        if not self.credentials_configured:
            raise ValueError("Google OAuth credentials not configured")

        code_verifier = self._code_verifiers.get(state)
        if not code_verifier:
            raise ValueError("OAuth state not found or expired. Please try connecting again.")

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=[settings.gmail_scopes],
            redirect_uri=settings.google_redirect_uri,
        )

        flow.redirect_uri = settings.google_redirect_uri
        flow.code_verifier = code_verifier
        flow.fetch_token(code=code)

        credentials = flow.credentials
        self._tokens[state] = credentials

        # Clean up verifier after use
        del self._code_verifiers[state]

        logger.info("Successfully exchanged OAuth code for token")

    def get_credentials(self, state: str) -> Credentials | None:
        """Retrieve stored credentials for a session."""
        return self._tokens.get(state)

    def cancel_auth(self, state: str) -> bool:
        """Consume a pending OAuth state when Google denies authorization."""
        return self._code_verifiers.pop(state, None) is not None

    def search_emails(
        self,
        credentials: Credentials,
        query: str = "resume OR cv OR \"job application\"",
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Search Gmail for resume-related emails with attachments."""
        try:
            service = build("gmail", "v1", credentials=credentials)
            query = query.strip()
            gmail_query = (
                f"({query}) OR ({SUPPORTED_ATTACHMENT_QUERY})"
                if query
                else SUPPORTED_ATTACHMENT_QUERY
            )
            attachments = []
            messages_scanned = 0
            page_token = None

            while messages_scanned < max_results:
                page_size = min(100, max_results - messages_scanned)
                list_request = service.users().messages().list(
                    userId="me",
                    q=gmail_query,
                    maxResults=page_size,
                    pageToken=page_token,
                )
                results = list_request.execute()
                messages = results.get("messages") or []
                messages = messages[:page_size]

                for message in messages:
                    message_id = message.get("id")
                    if not message_id:
                        continue

                    msg_data = (
                        service.users()
                        .messages()
                        .get(userId="me", id=message_id, format="full")
                        .execute()
                    )

                    payload = msg_data.get("payload") or {}
                    headers = {
                        header["name"]: header["value"]
                        for header in payload.get("headers", [])
                        if "name" in header and "value" in header
                    }
                    parts = payload.get("parts") or [payload]
                    self._extract_attachments_from_parts(
                        message_id,
                        parts,
                        headers.get("Subject", "No Subject"),
                        headers.get("From", "Unknown"),
                        headers.get("Date", ""),
                        attachments,
                    )
                    email_body = self._extract_email_body(payload)
                    for item in attachments:
                        if item["message_id"] == message_id:
                            item["_email_body"] = email_body

                messages_scanned += len(messages)
                page_token = results.get("nextPageToken")
                if not page_token or not messages:
                    break

            logger.info(
                "Gmail attachment search completed: messages=%d supported_attachments=%d",
                messages_scanned,
                len(attachments),
            )
            return attachments

        except HttpError as e:
            status_code = getattr(getattr(e, "resp", None), "status", None)
            logger.error("Gmail API search failed (HTTP %s)", status_code)
            raise

    async def classify_attachments(
        self,
        credentials: Credentials,
        attachments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract and classify Gmail attachments without retaining document text."""
        pdf_extractor = PDFExtractionService()
        parser = ResumeParserService()
        llm = ProjectExtractionService()
        classified: list[dict[str, Any]] = []

        for attachment in attachments:
            attachment_key = (
                f"{attachment['message_id']}:{attachment['attachment_id']}"
            )
            cached = self._attachment_classifications.get(attachment_key)
            if cached:
                classified.append({**attachment, **cached})
                continue

            content = self.download_attachment(
                credentials,
                attachment["message_id"],
                attachment["attachment_id"],
            )
            content_hash = self.compute_file_hash(content)
            signals = self._document_signals_by_hash.get(content_hash)
            extracted_text: str | None = None

            if signals is None:
                try:
                    extracted_text = await self._extract_attachment_text(
                        content,
                        attachment["filename"],
                        pdf_extractor,
                    )
                    parsed = parser.parse(extracted_text)
                    signals = self._resume_signals(parsed, extracted_text)
                    self._document_signals_by_hash[content_hash] = signals
                except Exception:
                    logger.warning(
                        "Could not extract Gmail attachment for classification "
                        "(attachment_id=%s)",
                        attachment["attachment_id"],
                    )
                    result = {
                        "classification": "UNCERTAIN",
                        "confidence": 0.0,
                        "classification_reason": (
                            "Document text could not be extracted for review."
                        ),
                        "content_hash": content_hash,
                    }
                    self._attachment_classifications[attachment_key] = result
                    classified.append({**attachment, **result})
                    continue

            cached_document_result = self._document_classifications_by_hash.get(
                content_hash
            )
            if cached_document_result:
                result = dict(cached_document_result)
                result["content_hash"] = content_hash
                self._attachment_classifications[attachment_key] = result
                classified.append({**attachment, **result})
                continue

            result = await self._classify_document(
                signals,
                extracted_text or "",
                attachment,
                llm,
            )
            result["content_hash"] = content_hash
            self._document_classifications_by_hash[content_hash] = dict(result)
            self._attachment_classifications[attachment_key] = result
            classified.append({**attachment, **result})

        return classified

    async def _extract_attachment_text(
        self,
        content: bytes,
        filename: str,
        pdf_extractor: PDFExtractionService,
    ) -> str:
        extension = filename.rsplit(".", 1)[-1].lower()
        if extension == "pdf":
            result = await pdf_extractor.extract_from_bytes(
                content,
                source=filename,
            )
            return result.text
        if extension == "docx":
            return ResumeUploadService.extract_docx_text(content)
        raise ValueError("Legacy DOC text extraction is unavailable.")

    @staticmethod
    def _resume_signals(parsed: Any, text: str) -> dict[str, Any]:
        signals = {
            "candidate_name": bool(parsed.candidate_name),
            "email": bool(parsed.email),
            "phone": bool(parsed.phone),
            "skills": len(parsed.skills),
            "education": len(parsed.education),
            "experience": len(parsed.experiences),
            "projects": len(parsed.projects),
            "summary": bool(parsed.summary),
            "career_history": bool(
                re.search(
                    r"\b(19|20)\d{2}\b|\b(present|current|current role)\b",
                    text,
                    re.IGNORECASE,
                )
            ),
            "text_length": len(text.strip()),
        }
        return signals

    async def _classify_document(
        self,
        signals: dict[str, Any],
        text: str,
        attachment: dict[str, Any],
        llm: ProjectExtractionService,
    ) -> dict[str, Any]:
        if len(text.strip()) < MIN_CLASSIFICATION_TEXT_LENGTH:
            return {
                "classification": "UNCERTAIN",
                "confidence": 0.0,
                "classification_reason": (
                    "Insufficient readable text; manual review is recommended."
                ),
            }

        score = (
            12 * signals["candidate_name"]
            + 10 * signals["email"]
            + 10 * signals["phone"]
            + min(15, signals["skills"] * 3)
            + min(12, signals["education"] * 6)
            + min(20, signals["experience"] * 10)
            + min(12, signals["projects"] * 6)
            + 5 * signals["summary"]
            + 4 * signals["career_history"]
        )
        context = " ".join(
            (
                attachment.get("filename", ""),
                attachment.get("subject", ""),
                attachment.get("_email_body", ""),
            )
        )
        if RESUME_CONTEXT_PATTERN.search(context):
            score = min(100, score + 5)

        evidence = [
            label
            for key, label in (
                ("candidate_name", "candidate name"),
                ("email", "email address"),
                ("phone", "phone number"),
                ("skills", "skills"),
                ("education", "education"),
                ("experience", "work experience"),
                ("projects", "projects"),
                ("career_history", "career dates"),
            )
            if signals[key]
        ]
        has_structured_resume_data = any(
            signals[key] for key in ("skills", "education", "experience", "projects")
        )

        if (
            score >= 55
            and signals["candidate_name"]
            and (signals["email"] or signals["phone"] or has_structured_resume_data)
        ):
            return {
                "classification": "RESUME",
                "confidence": min(0.99, 0.65 + score / 300),
                "classification_reason": (
                    "Resume structure detected: " + ", ".join(evidence[:4]) + "."
                ),
            }

        if (
            score <= 25
            and NON_RESUME_PATTERN.search(
                f"{text}\n{context}"
            )
        ):
            return {
                "classification": "NON_RESUME",
                "confidence": 0.9,
                "classification_reason": (
                    "Document content indicates a non-resume document."
                ),
            }

        if text.strip() and self._llm_available is not False:
            try:
                prompt = (
                    "Classify this email attachment as RESUME, NON_RESUME, or "
                    "UNCERTAIN. Assess resume content, not filename alone. Look "
                    "for candidate name/contact, skills, education, work "
                    "experience, projects, and career history. Email subject "
                    "and body are supplementary context. Return only JSON with "
                    'keys "classification", "confidence" (0 to 1), and '
                    '"reason" (short). Parsed resume indicators: '
                    f"{json.dumps(signals)}\nFilename: "
                    f"{attachment.get('filename', '')}\nEmail subject: "
                    f"{attachment.get('subject', '')}\nEmail body: "
                    f"{attachment.get('_email_body', '')[:1000]}\n"
                    f"Document text:\n{text[:10000]}"
                )
                response = await asyncio.wait_for(
                    llm._call_ollama(prompt),
                    timeout=min(15, settings.ollama_timeout),
                )
                self._llm_available = True
                match = re.search(r"\{.*\}", response, re.DOTALL)
                if match:
                    answer = json.loads(match.group())
                    category = answer.get("classification")
                    confidence = float(answer.get("confidence", 0))
                    if (
                        category in {"RESUME", "NON_RESUME", "UNCERTAIN"}
                        and 0 <= confidence <= 1
                        and (
                            category != "RESUME"
                            or (signals["candidate_name"] and has_structured_resume_data)
                        )
                    ):
                        if category == "RESUME" and confidence < 0.75:
                            category = "UNCERTAIN"
                        elif category == "NON_RESUME" and confidence < 0.8:
                            category = "UNCERTAIN"
                        return {
                            "classification": category,
                            "confidence": confidence,
                            "classification_reason": str(
                                answer.get("reason", "Classified from document content.")
                            )[:240],
                        }
            except Exception:
                self._llm_available = False
                logger.info("Local AI classification unavailable; using review status.")

        if not text.strip():
            reason = "No readable document text; manual review is recommended."
        elif evidence:
            reason = "Some resume indicators found (" + ", ".join(evidence[:3]) + "); review needed."
        else:
            reason = "Insufficient resume indicators; manual review is recommended."
        return {
            "classification": "UNCERTAIN",
            "confidence": round(min(score, 55) / 100, 2),
            "classification_reason": reason,
        }

    @staticmethod
    def _extract_email_body(payload: dict[str, Any]) -> str:
        import base64

        chunks: list[str] = []

        def visit(part: dict[str, Any]) -> None:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    try:
                        chunks.append(
                            base64.urlsafe_b64decode(data).decode(
                                "utf-8",
                                errors="replace",
                            )
                        )
                    except (ValueError, TypeError):
                        pass
            for child in part.get("parts", []):
                visit(child)

        visit(payload)
        return "\n".join(chunks)[:4000]

    def _extract_attachments_from_parts(
        self,
        message_id: str,
        parts: list[dict[str, Any]],
        subject: str,
        sender: str,
        date: str,
        attachments: list[dict[str, Any]],
    ) -> None:
        """Recursively extract attachments from message parts."""
        for part in parts:
            filename = part.get("filename", "")
            mime_type = part.get("mimeType", "")

            # Check if this is an attachment (has filename and is document type)
            if filename and self._is_supported_file_type(mime_type, filename):
                attachment_id = part.get("body", {}).get("attachmentId")
                size = part.get("body", {}).get("size", 0)

                if attachment_id:
                    attachments.append(
                        {
                            "message_id": message_id,
                            "attachment_id": attachment_id,
                            "filename": filename,
                            "size": size,
                            "mime_type": mime_type,
                            "subject": subject,
                            "sender": sender,
                            "date": date,
                        }
                    )

            # Recursively check nested parts
            if "parts" in part:
                self._extract_attachments_from_parts(
                    message_id, part["parts"], subject, sender, date, attachments
                )

    def _is_supported_file_type(self, mime_type: str, filename: str) -> bool:
        """Check if file type is supported for resume import."""
        supported_mime_types = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        }

        if mime_type in supported_mime_types:
            return True

        # Check by extension
        filename_lower = filename.lower()
        return filename_lower.endswith((".pdf", ".docx", ".doc"))

    def download_attachment(
        self,
        credentials: Credentials,
        message_id: str,
        attachment_id: str,
    ) -> bytes:
        """Download attachment content from Gmail."""
        try:
            service = build("gmail", "v1", credentials=credentials)

            attachment = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            import base64

            data = attachment.get("data", "")
            return base64.urlsafe_b64decode(data)

        except HttpError as e:
            logger.error(f"Failed to download attachment: {e}")
            raise RuntimeError(f"Failed to download attachment: {e}")

    def compute_file_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of file content for deduplication."""
        return hashlib.sha256(content).hexdigest()

    def is_configured(self) -> bool:
        """Check if Gmail OAuth is configured."""
        return self.credentials_configured

    def is_connected(self, state: str | None = None) -> bool:
        """Check whether credentials are stored for any Gmail OAuth session."""
        if state is not None:
            credentials = self._tokens.get(state)
            return bool(
                credentials
                and (credentials.token or credentials.refresh_token)
            )
        return any(
            credentials.token or credentials.refresh_token
            for credentials in self._tokens.values()
        )

    def get_gmail_email(self, state: str) -> str | None:
        """Retrieve the Gmail email address for the connected account."""
        credentials = self._tokens.get(state)
        if not credentials:
            return None

        try:
            service = build("gmail", "v1", credentials=credentials)
            profile = service.users().getProfile(userId="me").execute()
            return profile.get("email")
        except Exception as e:
            logger.warning("Failed to retrieve Gmail profile: %s", e)
            return None

    def disconnect_account(self, state: str) -> bool:
        """Disconnect the Gmail account by removing stored credentials."""
        if state in self._tokens:
            del self._tokens[state]
            logger.info("Gmail account disconnected for state: %s", state)
            return True
        return False

    def switch_account(self) -> tuple[str, str]:
        """Generate OAuth authorization URL for account switching with prompt=select_account."""
        if not self.credentials_configured:
            raise ValueError(
                "Google OAuth credentials not configured. "
                "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
            )

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=[settings.gmail_scopes],
            redirect_uri=settings.google_redirect_uri,
        )

        state = secrets.token_urlsafe(16)
        flow.redirect_uri = settings.google_redirect_uri

        auth_url, returned_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="select_account",
            code_challenge_method="S256",
        )

        if not flow.code_verifier:
            raise ValueError("OAuth PKCE code verifier was not generated")

        self._code_verifiers[returned_state] = flow.code_verifier

        return auth_url, returned_state
