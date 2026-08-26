import re
from decimal import Decimal, InvalidOperation

_AMOUNT_RE = re.compile(
    r"(?:₹|rs\.?|inr|usd|\$)?\s*([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)


def parse_amount(value: str) -> Decimal | None:
    match = _AMOUNT_RE.search(value.strip())
    if not match:
        return None
    return _to_decimal(match.group(1))


def amounts_in_text(value: str) -> list[Decimal]:
    found: list[Decimal] = []
    for raw in _AMOUNT_RE.findall(value):
        amount = _to_decimal(raw)
        if amount is not None:
            found.append(amount)
    return found


def _to_decimal(raw: str) -> Decimal | None:
    normalized = raw.replace(",", "")
    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None
    if amount <= 0:
        return None
    return amount.quantize(Decimal("0.01")) if "." in normalized else amount


def detect_currency(value: str, default: str = "INR") -> str:
    lowered = value.lower()
    if "$" in value or "usd" in lowered:
        return "USD"
    return default
