"""
WhatsApp webhook endpoint for Twilio integration.

Handles incoming WhatsApp messages from Twilio, processes them
through the conversation orchestrator, and sends responses back.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, status
from pydantic import BaseModel

from src.integrations.twilio_client import send_whatsapp_message
from src.integrations.twilio_security import verify_twilio_signature
from src.orchestrator.graph import handle_turn
from src.safety.moderation import check_message
from src.safety.rate_limit import fixed_window_allow
from src.core.config import settings
from src.db.redis_client import get_redis


router = APIRouter()


class WebhookResponse(BaseModel):
    """Response model for webhook (Twilio expects 200 OK)"""
    status: str
    message: str


def extract_phone_number(whatsapp_id: str) -> str:
    """
    Extract phone number from Twilio's 'whatsapp:+1234567890' format.

    Args:
        whatsapp_id: Full WhatsApp ID from Twilio

    Returns:
        Phone number without 'whatsapp:' prefix
    """
    if whatsapp_id.startswith("whatsapp:"):
        return whatsapp_id[9:]  # Remove 'whatsapp:' prefix
    return whatsapp_id


@router.post(
    "/webhooks/whatsapp",
    response_model=WebhookResponse,
    dependencies=[Depends(verify_twilio_signature)],
    status_code=status.HTTP_200_OK,
)
async def whatsapp_webhook(
    From: str = Form(...),  # Sender's WhatsApp ID (e.g., whatsapp:+1234567890)
    To: str = Form(...),    # Bot's WhatsApp ID
    Body: str = Form(...),  # Message text
    MessageSid: str = Form(...),  # Unique message ID
) -> WebhookResponse:
    """
    Receive incoming WhatsApp messages from Twilio.

    This endpoint:
    1. Validates the request signature (via dependency)
    2. Extracts message details
    3. Applies moderation and rate limiting
    4. Processes message through conversation orchestrator
    5. Sends response back to user via WhatsApp

    Args:
        From: Sender's WhatsApp ID from Twilio
        To: Recipient WhatsApp ID (your bot)
        Body: Message text content
        MessageSid: Unique message identifier

    Returns:
        WebhookResponse with status and message
    """
    # Extract phone number to use as session_id
    phone_number = extract_phone_number(From)
    session_id = phone_number  # Use phone as session identifier

    # Apply content moderation
    if settings.moderation_enabled:
        moderation_result = check_message(Body)
        if not moderation_result.allowed:
            # Send safety policy message back to user
            error_message = (
                f"Your message was blocked by our safety policy ({moderation_result.category}). "
                "Please rephrase your request."
            )
            await send_whatsapp_message(From, error_message)

            return WebhookResponse(
                status="blocked",
                message=f"Message blocked: {moderation_result.category}"
            )

    # Apply rate limiting (per phone number)
    redis = await get_redis()
    rate_limit_key = f"rl:whatsapp:{phone_number}"
    rate_limit_result = await fixed_window_allow(
        redis,
        rate_limit_key,
        settings.rate_limit_chat_per_min,
        60
    )

    if not rate_limit_result.allowed:
        # Send rate limit message back to user
        error_message = (
            f"You're sending messages too quickly. "
            f"Please wait {rate_limit_result.reset_seconds} seconds and try again."
        )
        await send_whatsapp_message(From, error_message)

        return WebhookResponse(
            status="rate_limited",
            message=f"Rate limit exceeded for {phone_number}"
        )

    # Process message through conversation orchestrator
    try:
        # Collect full response from streaming handle_turn
        response_parts = []
        async for token in handle_turn(session_id, Body):
            # Skip intent markers (e.g., [intent:WEATHER])
            if not token.startswith("[intent:"):
                response_parts.append(token)

        # Build complete response
        response_text = "".join(response_parts) if response_parts else (
            "I'm not sure how to help with that. Try asking about the weather!"
        )

        # Send response back via WhatsApp
        send_result = await send_whatsapp_message(From, response_text)

        if not send_result["success"]:
            # Log error but still return 200 to Twilio (avoid retries)
            print(f"⚠️  Failed to send WhatsApp message: {send_result['error']}")
            return WebhookResponse(
                status="send_failed",
                message="Failed to send response message"
            )

        return WebhookResponse(
            status="success",
            message=f"Message processed and sent (SID: {send_result['message_sid']})"
        )

    except Exception as e:
        # Log error and return 200 to Twilio (avoid infinite retries)
        print(f"❌ Error processing WhatsApp message: {str(e)}")

        # Try to send error message to user
        error_message = "Sorry, I encountered an error processing your message. Please try again."
        await send_whatsapp_message(From, error_message)

        return WebhookResponse(
            status="error",
            message=f"Error: {str(e)}"
        )


@router.get("/webhooks/whatsapp")
async def whatsapp_webhook_verification():
    """
    Simple GET endpoint for webhook verification during Twilio setup.

    Some webhook configurations require a GET endpoint to verify
    the URL is valid before accepting POST requests.
    """
    return {"status": "ok", "message": "WhatsApp webhook is active"}
