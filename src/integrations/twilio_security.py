"""
Twilio webhook security validation.

Implements signature verification to ensure webhook requests
are genuinely from Twilio and not from malicious actors.
"""

from typing import Optional

from fastapi import Header, HTTPException, Request, status
from twilio.request_validator import RequestValidator

from src.core.config import settings


def get_validator() -> RequestValidator:
    """
    Get Twilio request validator instance.

    Returns:
        Configured RequestValidator

    Raises:
        ValueError: If auth token is not configured
    """
    if not settings.twilio_auth_token:
        raise ValueError("TWILIO_AUTH_TOKEN not configured")

    return RequestValidator(settings.twilio_auth_token)


async def verify_twilio_signature(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None),
) -> None:
    """
    FastAPI dependency to verify Twilio webhook signature.

    Validates that the request is genuinely from Twilio by checking
    the X-Twilio-Signature header against expected value.

    Args:
        request: FastAPI Request object
        x_twilio_signature: Signature from Twilio header

    Raises:
        HTTPException: If signature is missing or invalid
    """
    if not x_twilio_signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Twilio-Signature header"
        )

    # Get the full URL that Twilio called
    url = str(request.url)

    # Get form data as dict
    form_data = await request.form()
    params = dict(form_data)

    # Validate signature
    validator = get_validator()
    is_valid = validator.validate(url, params, x_twilio_signature)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio signature"
        )
