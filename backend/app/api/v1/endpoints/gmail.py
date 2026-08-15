from fastapi import APIRouter, Depends, Request
from app.integration.gmail.token_store import save_token
from app.integration.gmail.client import GmailClient
from app.api.deps import get_gmail_ingestion_service
from app.services.gmail_ingestion import GmailIngestionService
from app.integration.gmail.auth import GmailAuth


router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"],
)

gmail_auth = GmailAuth()


@router.get("/login")
async def gmail_login(request: Request):
    authorization_url, state, code_verifier = (
        gmail_auth.get_authorization_url()
    )

    request.session["oauth_state"] = state
    request.session["code_verifier"] = code_verifier

    return {
        "authorization_url": authorization_url
    }


@router.get("/callback")
async def gmail_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        return {
            "error": "Authorization code not received"
        }

    saved_state = request.session.get("oauth_state")
    code_verifier = request.session.get("code_verifier")

    if not saved_state:
        return {
            "error": "OAuth state not found"
        }

    if state != saved_state:
        return {
            "error": "Invalid OAuth state"
        }

    if not code_verifier:
        return {
            "error": "PKCE code verifier not found"
        }

    credentials = gmail_auth.fetch_token(
        code=code,
        code_verifier=code_verifier,
    )

    save_token({
    "token": credentials.token,
    "refresh_token": credentials.refresh_token,
    "token_uri": credentials.token_uri,
    "client_id": credentials.client_id,
    "client_secret": credentials.client_secret,
    "scopes": credentials.scopes,
})

    request.session.pop("oauth_state", None)
    request.session.pop("code_verifier", None)

    return {
        "message": "Gmail authentication successful",
        "token_received": bool(credentials.token),
        "refresh_token_received": bool(credentials.refresh_token),
    }

@router.get("/messages")
async def gmail_messages():
    gmail_client = GmailClient()

    messages = gmail_client.list_messages(
        max_results=10
    )

    return {
        "count": len(messages),
        "messages": messages,
    }
@router.get("/attachments")
async def gmail_attachments():
    gmail_client = GmailClient()

    attachments = gmail_client.list_attachments(
        max_results=10
    )

    return {
        "count": len(attachments),
        "attachments": attachments,
    }

@router.get("/attachments/{message_id}/{attachment_id}")
async def download_gmail_attachment(
    message_id: str,
    attachment_id: str,
    filename: str = "resume.pdf",
):
    gmail_client = GmailClient()

    try:
        file_path = gmail_client.download_attachment(
            message_id=message_id,
            attachment_id=attachment_id,
            filename=filename,
        )

        return {
            "message": "Attachment downloaded successfully",
            "filename": filename,
            "path": file_path,
        }

    except Exception as e:
        return {
            "error": type(e).__name__,
            "detail": str(e),
        }

@router.post("/process-resumes")
async def process_gmail_resumes(
    service: GmailIngestionService = Depends(
        get_gmail_ingestion_service
    ),
):
    results = await service.process_resume_emails(
        max_results=10
    )

    return {
        "count": len(results),
        "results": results,
    }