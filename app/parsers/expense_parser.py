import re
from app.core.categories import map_category
from app.schemas.expense import ParsedExpense
from app.utils.money import detect_currency, parse_amount

_COMPLEX_HINTS = re.compile(
    r"\b(spent|paid|bought|yesterday|today|tomorrow|last|for|with|on|and)\b",
    re.IGNORECASE,
)

_SIMPLE_RE = re.compile(
    r"^\s*(?:₹|rs\.?|inr|usd|\$)?\s*"
    r"(?P<amount>[0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)"
    r"\s+(?P<rest>.+?)\s*$",
    re.IGNORECASE,
)


def parse_simple_expense(message: str) -> ParsedExpense | None:
    """Parse high-confidence simple expenses such as '₹450 Uber'. Return None if uncertain."""
    if not message or not message.strip():
        return None
    if "\n" in message.strip():
        return None

    match = _SIMPLE_RE.match(message)
    if not match:
        return None

    rest = match.group("rest").strip()
    if not rest or _COMPLEX_HINTS.search(rest):
        return None
    if len(rest.split()) > 4:
        return None

    amount = parse_amount(match.group("amount"))
    if amount is None:
        return None

    merchant = _normalize_merchant(rest)
    if not merchant:
        return None

    return ParsedExpense(
        amount=amount,
        currency=detect_currency(message),
        merchant=merchant,
        category=map_category(rest),
        confident=True,
    )


def _normalize_merchant(value: str) -> str:
    return " ".join(part.capitalize() if part.islower() else part for part in value.split())
