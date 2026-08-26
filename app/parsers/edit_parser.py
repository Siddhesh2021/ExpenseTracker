import re
from dataclasses import dataclass

from app.core.categories import is_allowed_category, normalize_category
from app.schemas.expense import ExpenseExtraction, ExtractionContext
from app.utils.dates import parse_relative_date
from app.utils.money import parse_amount

_FIELD_ALIASES = {
    "amount": "amount",
    "merchant": "merchant",
    "vendor": "merchant",
    "category": "category",
    "date": "expense_date",
    "expense date": "expense_date",
    "client": "client",
    "project": "project",
    "description": "description",
    "desc": "description",
}

_EDIT_RE = re.compile(
    r"^(?:please\s+)?(?:change|set|update|make)\s+"
    r"(?P<field>amount|merchant|vendor|category|date|expense\s+date|client|project|description|desc)"
    r"\s+(?:to|as|:)\s+(?P<value>.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedEdit:
    field: str
    value: str


def parse_edit(text: str) -> ParsedEdit | None:
    match = _EDIT_RE.match(" ".join(text.strip().split()))
    if not match:
        return None
    field = _FIELD_ALIASES.get(match.group("field").strip().lower())
    value = match.group("value").strip()
    if not field or not value:
        return None
    return ParsedEdit(field=field, value=value)


def apply_edit(
    extraction: ExpenseExtraction,
    edit: ParsedEdit,
    context: ExtractionContext,
) -> ExpenseExtraction | None:
    if edit.field == "amount":
        amount = parse_amount(edit.value)
        if amount is None:
            return None
        return extraction.model_copy(update={"amount": amount, "needs_confirmation": True})

    if edit.field == "category":
        if not is_allowed_category(edit.value):
            return None
        return extraction.model_copy(update={"category": normalize_category(edit.value), "needs_confirmation": True})

    if edit.field == "expense_date":
        parsed_date = parse_relative_date(edit.value, context.timezone, now=context.today)
        if parsed_date is None:
            return None
        return extraction.model_copy(update={"expense_date": parsed_date, "needs_confirmation": True})

    if edit.field in {"merchant", "client", "project", "description"}:
        return extraction.model_copy(update={edit.field: edit.value.strip(), "needs_confirmation": True})

    return None


def require_complete_extraction(extraction: ExpenseExtraction) -> ExpenseExtraction | None:
    try:
        validated = ExpenseExtraction.model_validate(extraction.model_dump())
    except Exception:
        return None
    if validated.amount is None or validated.amount <= 0:
        return None
    return validated
