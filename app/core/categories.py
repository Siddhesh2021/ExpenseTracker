from typing import Literal

ALLOWED_CATEGORIES = (
    "Travel",
    "Food",
    "Software",
    "Office",
    "Marketing",
    "Equipment",
    "Utilities",
    "Client Expense",
    "Other",
)

Category = Literal[
    "Travel",
    "Food",
    "Software",
    "Office",
    "Marketing",
    "Equipment",
    "Utilities",
    "Client Expense",
    "Other",
]

DEFAULT_CATEGORY: Category = "Other"

# Lowercase keyword -> canonical category. Keep this list easy to extend.
CATEGORY_KEYWORDS: dict[str, Category] = {
    "uber": "Travel",
    "ola": "Travel",
    "fuel": "Travel",
    "petrol": "Travel",
    "rapido": "Travel",
    "cab": "Travel",
    "taxi": "Travel",
    "flight": "Travel",
    "train": "Travel",
    "swiggy": "Food",
    "zomato": "Food",
    "restaurant": "Food",
    "lunch": "Food",
    "dinner": "Food",
    "breakfast": "Food",
    "cafe": "Food",
    "hostinger": "Software",
    "github": "Software",
    "vercel": "Software",
    "aws": "Software",
    "office": "Office",
    "stationery": "Office",
    "ads": "Marketing",
    "advertising": "Marketing",
    "laptop": "Equipment",
    "monitor": "Equipment",
    "electricity": "Utilities",
    "internet": "Utilities",
    "wifi": "Utilities",
}

_ALLOWED_LOOKUP = {name.lower(): name for name in ALLOWED_CATEGORIES}


def is_allowed_category(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _ALLOWED_LOOKUP


def normalize_category(value: str | None) -> Category:
    if value is None:
        return DEFAULT_CATEGORY
    matched = _ALLOWED_LOOKUP.get(value.strip().lower())
    if matched is None:
        return DEFAULT_CATEGORY
    return matched  # type: ignore[return-value]


def map_category(merchant_or_text: str) -> Category:
    tokens = [token.strip().lower() for token in merchant_or_text.replace("-", " ").split() if token.strip()]
    for token in tokens:
        category = CATEGORY_KEYWORDS.get(token)
        if category is not None:
            return category
    lowered = merchant_or_text.strip().lower()
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in lowered:
            return category
    return DEFAULT_CATEGORY
