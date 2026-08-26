import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.database import get_engine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("health_check_db_failed")
        return JSONResponse({"status": "error"}, status_code=503)
    return JSONResponse({"status": "ok"})
