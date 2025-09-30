import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from src.core.config import settings
from src.core.logging import logger
from src.db.redis_client import get_redis
from src.orchestrator.graph import handle_turn
from src.orchestrator.router import route
from src.safety.moderation import check_message
from src.safety.rate_limit import fixed_window_allow
from src.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    # Moderation
    if settings.moderation_enabled:
        m = check_message(req.message)
        if not m.allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Blocked by safety policy: {m.category}")

    # Chat rate limit
    r = await get_redis()
    rl_key = f"rl:chat:{req.session_id}"
    outcome = await fixed_window_allow(r, rl_key, settings.rate_limit_chat_per_min, 60)
    if not outcome.allowed:
        raise HTTPException(status_code=429, detail="Chat rate limit exceeded. Please wait a bit.")

    logger.info(f"[{req.session_id}] user: {req.message}")
    routed = route(req.message)
    logger.info(f"[{req.session_id}] routed -> {routed.intent} ({routed.reason})")
    reply = f"Echo: {req.message}"
    return ChatResponse(session_id=req.session_id, reply=reply)

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

@router.get("/chat/stream")
async def chat_stream(session_id: str = Query(...), message: str = Query(...)):
    # Moderation
    if settings.moderation_enabled:
        m = check_message(message)
        if not m.allowed:
            async def blocked():
                yield _sse({"type": "error", "message": f"Blocked by safety policy: {m.category}"})
            return StreamingResponse(blocked(), media_type="text/event-stream")

    # Chat rate limit
    r = await get_redis()
    rl_key = f"rl:chat:{session_id}"
    outcome = await fixed_window_allow(r, rl_key, settings.rate_limit_chat_per_min, 60)
    if not outcome.allowed:
        async def limited():
            yield _sse({"type": "error", "message": "Chat rate limit exceeded. Please wait a bit."})
        return StreamingResponse(limited(), media_type="text/event-stream")

    logger.info(f"[{session_id}] (SSE) user: {message}")
    routed = route(message)
    logger.info(f"[{session_id}] routed -> {routed.intent} ({routed.reason})")

    async def event_gen() -> AsyncIterator[bytes]:
        yield _sse({"type": "route", "intent": routed.intent}).encode()
        async for tok in handle_turn(session_id, message):
            yield _sse({"type": "token", "text": tok}).encode()
        yield _sse({"type": "done"}).encode()

    return StreamingResponse(event_gen(), media_type="text/event-stream")

@router.websocket("/ws")
async def chat_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)
            session_id = payload.get("session_id", "ws")
            message = payload.get("message", "")

            # Moderation
            if settings.moderation_enabled:
                m = check_message(message)
                if not m.allowed:
                    await ws.send_text(json.dumps({"type": "error", "message": f"Blocked by safety policy: {m.category}"}))
                    continue

            # Chat rate limit
            r = await get_redis()
            rl_key = f"rl:chat:{session_id}"
            outcome = await fixed_window_allow(r, rl_key, settings.rate_limit_chat_per_min, 60)
            if not outcome.allowed:
                await ws.send_text(json.dumps({"type": "error", "message": "Chat rate limit exceeded. Please wait a bit."}))
                continue

            logger.info(f"[{session_id}] (WS) user: {message}")
            routed = route(message)
            await ws.send_text(json.dumps({"type": "route", "intent": routed.intent}))
            async for tok in handle_turn(session_id, message):
                await ws.send_text(json.dumps({"type": "token", "text": tok}))
            await ws.send_text(json.dumps({"type": "done"}))
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
