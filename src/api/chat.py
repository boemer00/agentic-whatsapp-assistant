import json
from typing import AsyncIterator

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from src.core.logging import logger
from src.orchestrator.graph import handle_turn
from src.orchestrator.router import route
from src.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    logger.info(f"[{req.session_id}] user: {req.message}")
    # (Optional) First-turn routing info, not used by echo yet:
    r = route(req.message)
    logger.info(f"[{req.session_id}] routed -> {r.intent} ({r.reason})")
    reply = f"Echo: {req.message}"
    return ChatResponse(session_id=req.session_id, reply=reply)


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.get("/chat/stream")
async def chat_stream(
    session_id: str = Query(...),
    message: str = Query(...),
):
    logger.info(f"[{session_id}] (SSE) user: {message}")
    r = route(message)
    logger.info(f"[{session_id}] routed -> {r.intent} ({r.reason})")

    async def event_gen() -> AsyncIterator[bytes]:
        # Optional meta event (e.g., routing)
        yield _sse_event({"type": "route", "intent": r.intent}).encode()
        # Token stream
        async for tok in handle_turn(session_id, message):
            yield _sse_event({"type": "token", "text": tok}).encode()
        # Done
        yield _sse_event({"type": "done"}).encode()

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
            logger.info(f"[{session_id}] (WS) user: {message}")
            r = route(message)
            await ws.send_text(json.dumps({"type": "route", "intent": r.intent}))
            async for tok in handle_turn(session_id, message):
                await ws.send_text(json.dumps({"type": "token", "text": tok}))
            await ws.send_text(json.dumps({"type": "done"}))
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception(e)
        # Surface a final error frame to client (optional)
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
        await ws.close()
