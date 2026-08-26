from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.webhook import router as webhook_router
from app.core.logging import setup_logging
from app.db import models as _models  # noqa: F401


def create_app() -> FastAPI:
    setup_logging()
    application = FastAPI(title="ExpenseTracker", version="0.1.0")
    application.include_router(health_router)
    application.include_router(webhook_router)
    return application


app = create_app()
