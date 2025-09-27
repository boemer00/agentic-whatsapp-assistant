from fastapi import APIRouter
from src.schemas.chat import ChatRequest, ChatResponse
from src.core.logging import logger

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    # For now: simple echo with a friendly prefix.
    logger.info(f"[{req.session_id}] user: {req.message}")
    reply = f"Echo: {req.message}"
    return ChatResponse(session_id=req.session_id, reply=reply)
