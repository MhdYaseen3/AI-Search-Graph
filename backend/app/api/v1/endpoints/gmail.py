import io
import json
import logging
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse
from googleapiclient.errors import HttpError

from app.api.deps import (
    get_gmail_message_tracking_service,
    get_resume_ingest_service,
)
from app.core.config import settings
from app.core.exceptions import AppException
from app.schemas.gmail import (
    GmailAttachment,
    GmailAuthUrlResponse,
    GmailConnectionStatus,
    GmailImportHistoryItem,
    GmailImportRequest,
    GmailImportRetryRequest,
    GmailImportItemResult,
    GmailImportResponse,
    GmailSearchRequest,
)
from app.services.gmail_ingestion import GmailIngestionService
from app.services.gmail_message_tracking import GmailMessageTrackingService
from app.services.resume_ingest import ResumeIngestService
from starlette.datastructures import Headers

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"],
)

# Singleton service instance
_gmail_service = GmailIngestionService()


def get_gmail_service() -> GmailIngestionService:
    return _gmail_service


@router.get("/status", response_model=GmailConnectionStatus)
async def check_gmail_status(
    state: str | None = Query(None),
    service: GmailIngestionService = Depends(get_gmail_service),
) -> GmailConnectionStatus:
    """Check if Gmail OAuth is configured and connected."""
    email = None
    if state and service.is_connected(state):
        email = service.get_gmail_email(state)
    return GmailConnectionStatus(
        configured=service.is_configured(),
        connected=service.is_connected(state),
        email=email,
    )


@router.get("/auth-url", response_model=GmailAuthUrlResponse)
async def get_auth_url(
    service: GmailIngestionService = Depends(get_gmail_service),
) -> GmailAuthUrlResponse:
    """Generate OAuth authorization URL for Gmail connection."""
    try:
        auth_url, state = service.get_auth_url()
        return GmailAuthUrlResponse(auth_url=auth_url, state=state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/disconnect")
async def disconnect_gmail(
    state: str = Query(...),
    service: GmailIngestionService = Depends(get_gmail_service),
) -> dict[str, str]:
    """Disconnect the currently connected Gmail account."""
    if not service.is_connected(state):
        raise HTTPException(status_code=400, detail="No Gmail account is currently connected")
    
    success = service.disconnect_account(state)
    if success:
        return {"message": "Gmail account disconnected successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to disconnect Gmail account")


@router.get("/switch-account", response_model=GmailAuthUrlResponse)
async def switch_gmail_account(
    state: str = Query(...),
    service: GmailIngestionService = Depends(get_gmail_service),
) -> GmailAuthUrlResponse:
    """Generate OAuth authorization URL for switching Gmail accounts."""
    if not service.is_connected(state):
        raise HTTPException(status_code=400, detail="No Gmail account is currently connected")

    try:
        # Store the old state for later cleanup after successful authentication
        auth_url, new_state = service.switch_account()
        # Note: We keep the old credentials until successful authentication
        # The frontend will handle switching to the new state after success
        return GmailAuthUrlResponse(auth_url=auth_url, state=new_state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback", response_class=HTMLResponse)
async def oauth_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    service: GmailIngestionService = Depends(get_gmail_service),
) -> HTMLResponse:
    """Handle OAuth callback and store credentials."""
    origin = urlsplit(settings.frontend_origin)
    frontend_origin = f"{origin.scheme}://{origin.netloc}"
    try:
        if error:
            if not state or not service.cancel_auth(state):
                raise ValueError("OAuth state is invalid or expired.")
            if error == "access_denied":
                raise ValueError("Google authorization was denied.")
            message = "Google authorization failed."
            if error_description:
                message = f"{message} {error_description[:500]}"
            raise ValueError(message)
        if not code:
            raise ValueError("Google did not return an authorization code.")
        if not state:
            raise ValueError("Google did not return an OAuth state.")

        service.exchange_code_for_token(code, state)
        return _oauth_callback_page(
            frontend_origin,
            {"type": "gmail_oauth_callback", "success": True, "state": state},
            "Authentication successful. You can close this window.",
        )
    except ValueError as e:
        logger.warning("Gmail OAuth callback was rejected: %s", e)
        return _oauth_callback_page(
            frontend_origin,
            {
                "type": "gmail_oauth_callback",
                "success": False,
                "error": str(e),
                "state": state,
            },
            "Authentication failed. You can close this window.",
        )
    except Exception:
        logger.exception("Gmail OAuth callback failed")
        return _oauth_callback_page(
            frontend_origin,
            {
                "type": "gmail_oauth_callback",
                "success": False,
                "error": "Gmail authentication failed. Please try again.",
                "state": state,
            },
            "Authentication failed. You can close this window.",
        )


def _oauth_callback_page(
    frontend_origin: str,
    message: dict[str, Any],
    visible_message: str,
) -> HTMLResponse:
    """Render a safely encoded popup message for the configured frontend."""
    payload = (
        json.dumps(message)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    target_origin = json.dumps(frontend_origin)
    html = f"""<!doctype html>
<html>
<head><title>Gmail OAuth</title></head>
<body>
    <p>{visible_message}</p>
    <script>
        if (window.opener) {{
            window.opener.postMessage({payload}, {target_origin});
            window.close();
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/search")
async def search_emails(
    request: GmailSearchRequest,
    state: str = Query(...),
    service: GmailIngestionService = Depends(get_gmail_service),
) -> list[GmailAttachment]:
    """Search Gmail for resume-related emails with attachments."""
    credentials = service.get_credentials(state)
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated with Gmail")

    if not credentials.valid and not credentials.refresh_token:
        raise HTTPException(status_code=401, detail="Gmail credentials expired")

    try:
        results = service.search_emails(
            credentials,
            query=request.query,
            max_results=request.max_results,
        )
        results = await service.classify_attachments(credentials, results)
        return [GmailAttachment(**item) for item in results]
    except HttpError as e:
        status_code = getattr(getattr(e, "resp", None), "status", None)
        if status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Gmail authorization expired. Reconnect Gmail.",
            ) from e
        if status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="Gmail API access denied. Verify Gmail permissions and consent.",
            ) from e
        raise HTTPException(
            status_code=502,
            detail="Gmail API search failed. Please try again.",
        ) from e
    except RuntimeError as e:
        logger.warning("Gmail attachment classification failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Unable to download or classify Gmail attachments.",
        ) from e


@router.post("/import", response_model=GmailImportResponse)
async def import_attachments(
    request: GmailImportRequest,
    state: str = Query(...),
    gmail_service: GmailIngestionService = Depends(get_gmail_service),
    ingest_service: ResumeIngestService = Depends(get_resume_ingest_service),
    tracking_service: GmailMessageTrackingService = Depends(
        get_gmail_message_tracking_service
    ),
) -> GmailImportResponse:
    """Import selected Gmail attachments as resumes."""
    credentials = gmail_service.get_credentials(state)
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated with Gmail")

    results: list[GmailImportItemResult] = []
    seen_attachments: set[tuple[str, str]] = set()

    for attachment in request.attachments:
        message_id = attachment.message_id.strip()
        attachment_id = attachment.attachment_id.strip()
        result = GmailImportItemResult(
            message_id=message_id,
            attachment_id=attachment_id,
            filename=attachment.filename,
            success=False,
            status="PENDING",
        )
        key = (message_id, attachment_id)
        claimed = False
        sha256: str | None = None
        try:
            if not message_id or not attachment_id:
                raise ValueError("Gmail message and attachment identifiers are required.")
            if key in seen_attachments:
                raise ValueError("Attachment was selected more than once.")
            seen_attachments.add(key)
            if attachment.classification == "NON_RESUME":
                raise ValueError("Non-resume attachments cannot be imported.")
            if not credentials.valid and not credentials.refresh_token:
                raise ValueError("Gmail authorization expired. Reconnect Gmail.")

            claim = await tracking_service.claim_attachment(
                message_id,
                attachment_id,
                attachment.filename,
            )
            result.status = claim.get("status", "PENDING")
            result.candidate_id = claim.get("candidate_id")
            if not claim.get("claimed"):
                result.success = result.status == "SUCCESS"
                if result.status == "DUPLICATE":
                    result.sha256 = claim.get("sha256")
                    result.warning = "Matching file content was imported previously."
                elif result.status == "PROCESSING":
                    result.error = "This attachment is already being processed."
                elif result.status == "SUCCESS":
                    result.warning = "This Gmail attachment was already imported."
                results.append(result)
                continue
            claimed = True

            content = gmail_service.download_attachment(
                credentials,
                message_id,
                attachment_id,
            )
            sha256 = gmail_service.compute_file_hash(content)
            await tracking_service.set_attachment_hash(
                message_id,
                attachment_id,
                sha256,
            )

            hash_claim = await tracking_service.claim_hash(
                message_id,
                attachment_id,
                sha256,
            )
            if hash_claim.get("duplicate"):
                await tracking_service.mark_duplicate(
                    message_id,
                    attachment_id,
                    sha256,
                    hash_claim.get("candidate_id"),
                )
                result.status = "DUPLICATE"
                result.sha256 = sha256
                result.candidate_id = hash_claim.get("candidate_id")
                result.warning = "Matching file content was imported previously."
                results.append(result)
                continue
            if hash_claim.get("busy"):
                await tracking_service.mark_pending(
                    message_id,
                    attachment_id,
                    "Matching file content is currently being imported.",
                )
                result.status = "PENDING"
                result.sha256 = sha256
                result.error = "Matching file content is currently being imported."
                results.append(result)
                continue

            file_like = io.BytesIO(content)
            upload_file = UploadFile(
                file=file_like,
                filename=attachment.filename,
                headers=Headers({"content-type": attachment.mime_type}),
            )

            ingest_result = await ingest_service.ingest_gmail_attachment(
                file=upload_file,
                content=content,
                message_id=message_id,
                attachment_id=attachment_id,
                sha256=sha256,
            )

            result.success = True
            result.candidate_id = ingest_result.candidate_id
            result.status = "SUCCESS"
            result.sha256 = sha256
        except Exception as exc:
            reason = _safe_import_failure(exc)
            result.error = reason
            result.status = "FAILED"
            result.sha256 = sha256
            if claimed:
                try:
                    await tracking_service.mark_failed(
                        message_id,
                        attachment_id,
                        reason,
                        sha256,
                    )
                except Exception as status_error:
                    logger.error(
                        "Could not persist Gmail import failure status "
                        "(message_id=%s, attachment_id=%s, error_type=%s)",
                        message_id,
                        attachment_id,
                        type(status_error).__name__,
                    )
            logger.error(
                "Failed to import Gmail attachment "
                "(message_id=%s, attachment_id=%s, error_type=%s)",
                message_id,
                attachment_id,
                type(exc).__name__,
            )
        results.append(result)

    successes = [item for item in results if item.success]
    errors = [
        f"{item.filename}: {item.error}"
        for item in results
        if item.status == "FAILED" and item.error
    ]

    return GmailImportResponse(
        success_count=len(successes),
        failure_count=sum(item.status == "FAILED" for item in results),
        errors=errors,
        imported_candidates=[
            item.candidate_id
            for item in successes
            if item.candidate_id is not None
        ],
        results=results,
    )


@router.get("/import-history", response_model=list[GmailImportHistoryItem])
async def get_import_history(
    limit: int = Query(default=100, ge=1, le=500),
    tracking_service: GmailMessageTrackingService = Depends(
        get_gmail_message_tracking_service
    ),
) -> list[GmailImportHistoryItem]:
    """Return attachment import status and candidate identity only."""
    records = await tracking_service.list_import_history(limit)
    history = []
    for row in records:
        record = row.get("import", {})
        status = record.get("status") or (
            "SUCCESS" if record.get("candidate_id") else "FAILED"
        )
        history.append(
            GmailImportHistoryItem(
                message_id=record.get("message_id", ""),
                attachment_id=record.get("attachment_id", ""),
                filename=record.get("filename") or "Attachment",
                sha256=record.get("sha256"),
                status=status,
                imported_at=record.get("imported_at") or record.get("processed_at"),
                updated_at=record.get("updated_at"),
                candidate_id=row.get("candidate_id") or record.get("candidate_id"),
                candidate_name=row.get("candidate_name"),
                failure_reason=record.get("failure_reason"),
            )
        )
    return history


@router.post("/import/retry", response_model=GmailImportResponse)
async def retry_failed_import(
    request: GmailImportRetryRequest,
    state: str = Query(...),
    gmail_service: GmailIngestionService = Depends(get_gmail_service),
    ingest_service: ResumeIngestService = Depends(get_resume_ingest_service),
    tracking_service: GmailMessageTrackingService = Depends(
        get_gmail_message_tracking_service
    ),
) -> GmailImportResponse:
    credentials = gmail_service.get_credentials(state)
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated with Gmail")
    if not credentials.valid and not credentials.refresh_token:
        raise HTTPException(status_code=401, detail="Gmail credentials expired")

    record = await tracking_service.get_attachment_import(
        request.message_id,
        request.attachment_id,
    )
    if not record or record.get("status") not in {"FAILED", "PENDING"}:
        raise HTTPException(
            status_code=409,
            detail="Only failed or pending Gmail imports can be retried.",
        )

    filename = record.get("filename") or "resume.pdf"
    extension = filename.rsplit(".", 1)[-1].lower()
    mime_type = {
        "pdf": "application/pdf",
        "docx": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    }.get(extension, "application/octet-stream")
    attachment = GmailAttachment(
        message_id=request.message_id,
        attachment_id=request.attachment_id,
        filename=filename,
        size=0,
        mime_type=mime_type,
        subject="",
        sender="",
        date="",
        classification="RESUME",
    )
    return await import_attachments(
        GmailImportRequest(attachments=[attachment]),
        state,
        gmail_service,
        ingest_service,
        tracking_service,
    )


def _safe_import_failure(error: Exception) -> str:
    if isinstance(error, AppException):
        return error.message[:300]
    if isinstance(error, ValueError):
        return str(error)[:300]
    if isinstance(error, HttpError):
        return "Gmail API request failed."
    return "Unable to download or process this attachment."
