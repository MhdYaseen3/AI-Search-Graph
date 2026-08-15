from google_auth_oauthlib.flow import Flow

from app.core.config import settings


class GmailAuth:
    """Handles Gmail OAuth 2.0 + PKCE authentication."""

    def __init__(self) -> None:
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri

    @property
    def client_config(self) -> dict:
        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

    def get_authorization_url(self):
        flow = Flow.from_client_config(
            self.client_config,
            scopes=settings.gmail_scopes.split(","),
        )

        flow.redirect_uri = self.redirect_uri

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        code_verifier = flow.code_verifier

        return authorization_url, state, code_verifier

    def fetch_token(self, code: str, code_verifier: str):
        flow = Flow.from_client_config(
            self.client_config,
            scopes=settings.gmail_scopes.split(","),
        )

        flow.redirect_uri = self.redirect_uri

        flow.code_verifier = code_verifier

        flow.fetch_token(code=code)

        return flow.credentials