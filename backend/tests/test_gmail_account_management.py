"""Test Gmail account management (switch and disconnect)."""
import pytest
from unittest.mock import Mock, patch
from google.oauth2.credentials import Credentials


def test_get_gmail_email_success():
    """Test retrieving Gmail email address successfully."""
    with patch('app.services.gmail_ingestion.build') as mock_build:
        # Mock the Gmail API service
        mock_service = Mock()
        mock_service.users().getProfile.return_value.execute.return_value = {
            'email': 'test@example.com'
        }
        mock_build.return_value = mock_service

        from app.services.gmail_ingestion import GmailIngestionService
        service = GmailIngestionService()

        # Create mock credentials
        mock_creds = Mock(spec=Credentials)
        service._tokens['test-state'] = mock_creds

        # Test email retrieval
        email = service.get_gmail_email('test-state')
        assert email == 'test@example.com'


def test_get_gmail_email_no_credentials():
    """Test email retrieval with no credentials."""
    from app.services.gmail_ingestion import GmailIngestionService
    service = GmailIngestionService()

    # Test with no credentials
    email = service.get_gmail_email('nonexistent-state')
    assert email is None


def test_disconnect_account_success():
    """Test disconnecting a Gmail account."""
    from app.services.gmail_ingestion import GmailIngestionService
    service = GmailIngestionService()

    # Add mock credentials
    mock_creds = Mock(spec=Credentials)
    service._tokens['test-state'] = mock_creds

    # Test disconnect
    result = service.disconnect_account('test-state')
    assert result is True
    assert 'test-state' not in service._tokens


def test_disconnect_account_not_found():
    """Test disconnecting a non-existent account."""
    from app.services.gmail_ingestion import GmailIngestionService
    service = GmailIngestionService()

    # Test disconnect with non-existent state
    result = service.disconnect_account('nonexistent-state')
    assert result is False


def test_switch_account_generates_new_state():
    """Test that switch_account generates a new OAuth flow with select_account prompt."""
    with patch('app.services.gmail_ingestion.Flow') as mock_flow_class:
        from app.services.gmail_ingestion import GmailIngestionService
        from app.core.config import settings

        # Mock Flow to be configured
        service = GmailIngestionService()
        service.credentials_configured = True

        # Setup mock flow
        mock_flow = Mock()
        mock_flow_class.from_client_config.return_value = mock_flow
        mock_flow.authorization_url.return_value = ('http://auth.url', 'new-state')
        mock_flow.code_verifier = 'test-verifier'

        # Test switch account
        auth_url, state = service.switch_account()

        # Verify the flow was called with prompt='select_account'
        mock_flow.authorization_url.assert_called_once()
        call_kwargs = mock_flow.authorization_url.call_args[1]
        assert call_kwargs['prompt'] == 'select_account'

        # Verify new state was generated
        assert state == 'new-state'
        assert auth_url == 'http://auth.url'


def test_switch_account_requires_connection():
    """Test that switch_account requires an existing connection."""
    from app.services.gmail_ingestion import GmailIngestionService
    service = GmailIngestionService()

    # Test without configuration
    with pytest.raises(ValueError, match="Google OAuth credentials not configured"):
        service.switch_account()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
