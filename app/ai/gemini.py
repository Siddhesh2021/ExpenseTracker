import logging

from google import genai
from google.genai import types

from app.ai.base import AIProvider
from app.ai.exceptions import ExpenseExtractionError
from app.ai.prompts import build_system_prompt, build_user_prompt
from app.ai.validation import parse_gemini_json, validate_extraction_payload
from app.core.config import get_settings
from app.schemas.expense import ExpenseExtraction, ExtractionContext

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    def __init__(self, client: object | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._model = model or settings.gemini_model
        self._client = client or genai.Client(api_key=settings.gemini_api_key)

    def extract_expense(self, message: str, context: ExtractionContext) -> ExpenseExtraction:
        logger.info("gemini_invoked")
        prompt = build_user_prompt(
            message=message,
            today=context.today.isoformat(),
            timezone=context.timezone,
            currency=context.currency,
        )
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=build_system_prompt(),
                    response_mime_type="application/json",
                    temperature=0,
                ),
            )
        except Exception as exc:
            logger.exception("gemini_request_failed")
            raise ExpenseExtractionError("Gemini request failed") from exc

        raw = getattr(response, "text", None)
        if not raw:
            raise ExpenseExtractionError("empty Gemini response")
        payload = parse_gemini_json(raw)
        return validate_extraction_payload(payload, message, context)
