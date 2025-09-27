import asyncio
from typing import AsyncIterator

# Minimal COLLECT → RESPOND graph for MVP.
# For now it just streams an echo, token-by-token.
# Later you'll swap RESPOND with LLM streaming.


async def stream_echo(message: str) -> AsyncIterator[str]:
    """Yield tokens to simulate streaming generation."""
    prefix = "Echo: "
    for tok in (prefix + message).split():
        yield tok
        await asyncio.sleep(0.03)  # tiny delay to feel like streaming


async def handle_turn(session_id: str, message: str) -> AsyncIterator[str]:
    # Node: COLLECT (noop for echo MVP)
    # Node: RESPOND (echo stream)
    async for tok in stream_echo(message):
        yield tok
