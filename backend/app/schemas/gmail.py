from pydantic import BaseModel, Field
from typing import Literal, Optional

GmailImportStatus = Literal[
    "PENDING",
    "PROCESSING",
    "SUCCESS",
    "FAILED",
    "DUPLICATE",
]


class GmailAttachment(BaseModel):
    """Represents a Gmail attachment."""
    message_id: str
    attachment_id: str
    filename: str
    size: int
    mime_type: str
    subject: str
    sender: str
    date: str
    classification: Literal["RESUME", "NON_RESUME", "UNCERTAIN"] = "UNCERTAIN"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    classification_reason: str = "Document has not been classified."
    content_hash: str | None = None


class GmailSearchRequest(BaseModel):
    """Request to search Gmail for resume-related emails."""
    query: str = Field(default="resume OR cv OR \"job application\"", description="Gmail search query")
    max_results: int = Field(default=50, ge=1, le=100, description="Maximum emails to retrieve")


class GmailImportRequest(BaseModel):
    """Request to import selected Gmail attachments."""
    attachments: list[GmailAttachment]

class GmailImportRetryRequest(BaseModel):
    """Request to safely retry a previously failed Gmail attachment."""
    message_id: str
    attachment_id: str


class GmailImportItemResult(BaseModel):
    """Outcome for one explicitly selected Gmail attachment."""
    message_id: str
    attachment_id: str
    filename: str
    success: bool
    candidate_id: str | None = None
    status: GmailImportStatus
    sha256: str | None = None
    error: str | None = None
    warning: str | None = None


class GmailImportHistoryItem(BaseModel):
    """Privacy-minimal status and candidate details for one import attempt."""
    message_id: str
    attachment_id: str
    filename: str
    sha256: str | None = None
    status: GmailImportStatus
    imported_at: str | None = None
    updated_at: str | None = None
    candidate_id: str | None = None
    candidate_name: str | None = None
    failure_reason: str | None = None


class GmailImportResponse(BaseModel):
    """Response from Gmail import operation."""
    success_count: int
    failure_count: int
    errors: list[str] = Field(default_factory=list)
    imported_candidates: list[str] = Field(default_factory=list)
    results: list[GmailImportItemResult] = Field(default_factory=list)


class GmailAuthUrlResponse(BaseModel):
    """Response with OAuth authorization URL."""
    auth_url: str
    state: str


class GmailConnectionStatus(BaseModel):
    """Response checking Gmail connection status."""
    connected: bool
    configured: bool
    email: Optional[str] = None
