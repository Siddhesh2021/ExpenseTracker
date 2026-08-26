from app.ai.base import AIProvider
from app.ai.exceptions import ExpenseExtractionError
from app.ai.gemini import GeminiProvider
from app.core.config import get_settings


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return GeminiProvider()


__all__ = [
    "AIProvider",
    "ExpenseExtractionError",
    "GeminiProvider",
    "get_ai_provider",
]
