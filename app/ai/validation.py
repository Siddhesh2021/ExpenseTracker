import json
import logging
import re
from decimal import Decimal

from app.ai.exceptions import ExpenseExtractionError
from app.core.categories import is_allowed_category, normalize_category
from app.schemas.expense import ExpenseExtraction, ExtractionContext
from app.utils.money import amounts_in_text

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_gemini_json(raw: str) -> dict:
    if raw is None:
        raise ExpenseExtractionError("empty Gemini response")
    text = raw.strip()
    if not text:
        raise ExpenseExtractionError("empty Gemini response")
    text = _FENCE_RE.sub("", text).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExpenseExtractionError("invalid Gemini JSON") from exc
    if not isinstance(payload, dict):
        raise ExpenseExtractionError("Gemini JSON must be an object")
    return payload


def validate_extraction_payload(payload: dict, message: str, context: ExtractionContext) -> ExpenseExtraction:
    try:
        extraction = ExpenseExtraction.model_validate(payload)
    except Exception as exc:
        raise ExpenseExtractionError("Gemini data failed validation") from exc
    return ground_extraction(extraction, message, context)


def ground_extraction(extraction: ExpenseExtraction, message: str, context: ExtractionContext) -> ExpenseExtraction:
    """Reject invented amounts; drop invented merchants; never keep unknown categories."""
    updates: dict = {}
    if extraction.amount is not None and not _amount_is_grounded(extraction.amount, message):
        logger.info("gemini_amount_not_grounded")
        raise ExpenseExtractionError("Gemini invented an amount")

    if extraction.merchant and not _merchant_is_grounded(extraction.merchant, message):
        logger.info("gemini_merchant_not_grounded")
        updates["merchant"] = None

    if extraction.category and not is_allowed_category(extraction.category):
        updates["category"] = normalize_category(extraction.category)

    if extraction.currency is None:
        updates["currency"] = context.currency or "INR"

    if extraction.expense_date is not None and extraction.expense_date > context.today:
        logger.info("gemini_future_date_cleared")
        updates["expense_date"] = None

    if updates:
        extraction = extraction.model_copy(update=updates)
    return extraction


def _amount_is_grounded(amount: Decimal, message: str) -> bool:
    quantized = amount.quantize(Decimal("0.01")) if amount.as_tuple().exponent < 0 else amount
    mentioned = amounts_in_text(message)
    for candidate in mentioned:
        aligned = candidate.quantize(Decimal("0.01")) if candidate.as_tuple().exponent < 0 else candidate
        if aligned == quantized or candidate == amount:
            return True
    return False


def _merchant_is_grounded(merchant: str, message: str) -> bool:
    lowered = message.lower()
    value = merchant.strip().lower()
    if value in lowered:
        return True
    tokens = [token for token in re.split(r"\W+", value) if len(token) > 2]
    if not tokens:
        return False
    return all(token in lowered for token in tokens)
