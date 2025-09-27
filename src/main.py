from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.core.logging import setup_logging
from src.api.health import router as health_router
from src.api.chat import router as chat_router

def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(title="Agentic WhatsApp Assistant", version="0.1.0")

    # CORS (relax for local dev; tighten in prod)
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
        return {"ok": True, "service": "ai-assistant", "version": app.version}

    return app

app = create_app()
