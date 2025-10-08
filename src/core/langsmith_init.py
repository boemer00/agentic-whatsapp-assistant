"""
LangSmith initialization and verification.

This module ensures LangSmith tracing is properly configured.
"""

import os
from src.core.config import settings


def verify_langsmith_config() -> bool:
    """
    Verify LangSmith is properly configured for tracing.

    Returns:
        bool: True if LangSmith is configured, False otherwise
    """
    # Check if tracing is enabled
    if not settings.langsmith_tracing:
        print("ℹ️  LangSmith tracing is disabled")
        return False

    # Check required environment variables
    required_vars = {
        "LANGSMITH_API_KEY": os.getenv("LANGSMITH_API_KEY"),
        "LANGSMITH_PROJECT": os.getenv("LANGSMITH_PROJECT"),
    }

    missing = [k for k, v in required_vars.items() if not v]

    if missing:
        print(f"⚠️  LangSmith not fully configured. Missing: {', '.join(missing)}")
        print("   Traces will not be sent to LangSmith dashboard")
        return False

    # All checks passed
    project = required_vars["LANGSMITH_PROJECT"]
    endpoint = settings.langsmith_endpoint
    print(f"✅ LangSmith configured successfully")
    print(f"   Project: {project}")
    print(f"   Endpoint: {endpoint}")
    print(f"   View traces: https://smith.langchain.com/")
    return True


def verify_openai_config() -> bool:
    """
    Verify OpenAI is properly configured for LLM calls.

    Returns:
        bool: True if OpenAI is configured, False otherwise
    """
    if not settings.openai_api_key:
        print("⚠️  OpenAI not configured - will use keyword-based routing")
        return False

    model = settings.openai_model or "gpt-4o-mini"
    print(f"✅ OpenAI configured: {model}")
    return True


def print_startup_config():
    """Print configuration status on app startup."""
    print("\n" + "="*70)
    print("🚀 AI Assistant Starting Up")
    print("="*70)

    # Check LangSmith
    langsmith_ok = verify_langsmith_config()

    # Check OpenAI
    openai_ok = verify_openai_config()

    # Check Redis
    print(f"📦 Redis: {settings.redis_url}")

    # Summary
    print("\n" + "-"*70)
    if langsmith_ok and openai_ok:
        print("✅ All services configured - Full LLM + Tracing enabled")
    elif openai_ok:
        print("⚠️  Partial setup - LLM enabled but no LangSmith tracing")
    elif langsmith_ok:
        print("⚠️  Partial setup - LangSmith ready but no LLM (keyword routing)")
    else:
        print("⚠️  Basic mode - Keyword routing, no tracing")
    print("="*70 + "\n")
