"""Tests for Twilio client functionality."""

import pytest
from unittest.mock import Mock, patch
from src.integrations.twilio_client import get_twilio_client, send_whatsapp_message
from src.core.config import settings


def test_get_twilio_client_missing_credentials():
    """Test that client raises error when credentials are missing."""
    with patch.object(settings, 'twilio_account_sid', None):
        with patch.object(settings, 'twilio_auth_token', None):
            with pytest.raises(ValueError, match="Twilio credentials not configured"):
                get_twilio_client()


@pytest.mark.asyncio
async def test_send_whatsapp_message_missing_number():
    """Test that send fails when WhatsApp number is not configured."""
    with patch.object(settings, 'twilio_whatsapp_number', None):
        with pytest.raises(ValueError, match="Twilio WhatsApp number not configured"):
            await send_whatsapp_message("+1234567890", "Test message")


@pytest.mark.asyncio
async def test_send_whatsapp_message_adds_prefix():
    """Test that phone number gets whatsapp: prefix if missing."""
    with patch.object(settings, 'twilio_account_sid', 'test_sid'):
        with patch.object(settings, 'twilio_auth_token', 'test_token'):
            with patch.object(settings, 'twilio_whatsapp_number', 'whatsapp:+14155238886'):
                with patch('src.integrations.twilio_client.Client') as mock_client:
                    # Mock the Twilio client
                    mock_message = Mock()
                    mock_message.sid = "SM123"
                    mock_client.return_value.messages.create.return_value = mock_message

                    result = await send_whatsapp_message("+1234567890", "Test")

                    # Verify client was called with whatsapp: prefix
                    call_args = mock_client.return_value.messages.create.call_args
                    assert call_args[1]['to'] == "whatsapp:+1234567890"


@pytest.mark.asyncio
async def test_send_whatsapp_message_truncates_long_messages():
    """Test that messages longer than 1600 chars are truncated."""
    long_message = "A" * 2000  # 2000 characters

    with patch.object(settings, 'twilio_account_sid', 'test_sid'):
        with patch.object(settings, 'twilio_auth_token', 'test_token'):
            with patch.object(settings, 'twilio_whatsapp_number', 'whatsapp:+14155238886'):
                with patch('src.integrations.twilio_client.Client') as mock_client:
                    mock_message = Mock()
                    mock_message.sid = "SM123"
                    mock_client.return_value.messages.create.return_value = mock_message

                    result = await send_whatsapp_message("whatsapp:+1234567890", long_message)

                    # Verify message was truncated
                    call_args = mock_client.return_value.messages.create.call_args
                    sent_body = call_args[1]['body']
                    assert len(sent_body) == 1600
                    assert sent_body.endswith("...")
