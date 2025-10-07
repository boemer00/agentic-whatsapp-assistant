from dotenv import load_dotenv

# Load environment variables FIRST before any other imports
# This ensures LangSmith, OpenAI, and other env vars are available
load_dotenv()

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.api.health import router as health_router
from src.api.chat import router as chat_router
from src.core.langsmith_init import print_startup_config

def create_app() -> FastAPI:
    # Print configuration on startup
    print_startup_config()

    app = FastAPI(title="AI Assistant", version="0.1.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
         allow_headers=["*"],
         allow_credentials=True,
    )

    # Routers
    app.include_router(health_router, tags=["health"])
    app.include_router(chat_router, tags=["chat"])

    @app.get("/", tags=["root"])
    def root():
        return {
            "ok": True,
            "service": "ai-assistant",
            "version": app.version
            }

    return app

app = create_app()
