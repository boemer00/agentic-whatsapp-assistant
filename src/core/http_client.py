"""
Reusable async HTTP client for external API calls.

Provides a singleton AsyncClient with proper timeout and connection pooling.
"""

import httpx

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """
    Get or create a singleton async HTTP client.

    Returns:
        Configured AsyncClient with timeout and connection pooling
    """
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=10.0,  # 10 second timeout for all requests
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _client


async def close_http_client() -> None:
    """Close the HTTP client (call on app shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
