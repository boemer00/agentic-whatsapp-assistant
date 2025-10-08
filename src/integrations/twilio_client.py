"""
Twilio WhatsApp client for sending messages.

Provides a singleton Twilio REST client and helper functions for
sending WhatsApp messages via the Twilio API.
"""

from typing import Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from src.core.config import settings
from src.core.tracing import traceable


_client: Optional[Client] = None


def get_twilio_client() -> Client:
    """
    Get or create the singleton Twilio REST client.

    Returns:
        Initialized Twilio Client

    Raises:
        ValueError: If Twilio credentials are not configured
    """
    global _client

    if _client is None:
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            raise ValueError(
                "Twilio credentials not configured. "
                "Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env"
            )

        _client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    return _client


@traceable(name="send_whatsapp_message")
async def send_whatsapp_message(to: str, body: str) -> dict:
    """
    Send a WhatsApp message via Twilio.

    Args:
        to: Recipient phone number in format 'whatsapp:+1234567890'
        body: Message text content (max 1600 characters)

    Returns:
        dict with keys: success (bool), message_sid (str), error (str|None)

    Raises:
        ValueError: If configuration is invalid
    """
    if not settings.twilio_whatsapp_number:
        raise ValueError(
            "Twilio WhatsApp number not configured. "
            "Please set TWILIO_WHATSAPP_NUMBER in .env"
        )

    # Ensure phone number has 'whatsapp:' prefix
    if not to.startswith("whatsapp:"):
        to = f"whatsapp:{to}"

    # Split long messages (Twilio max: 1600 chars)
    if len(body) > 1600:
        body = body[:1597] + "..."

    try:
        client = get_twilio_client()

        message = client.messages.create(
            from_=settings.twilio_whatsapp_number,
            to=to,
            body=body
        )

        return {
            "success": True,
            "message_sid": message.sid,
            "error": None,
        }

    except TwilioRestException as e:
        # Log Twilio-specific errors
        error_msg = f"Twilio API error: {e.code} - {e.msg}"
        return {
            "success": False,
            "message_sid": None,
            "error": error_msg,
        }

    except Exception as e:
        # Catch any other errors
        error_msg = f"Unexpected error sending WhatsApp message: {str(e)}"
        return {
            "success": False,
            "message_sid": None,
            "error": error_msg,
        }
