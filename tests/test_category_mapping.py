from app.core.categories import ALLOWED_CATEGORIES, map_category, normalize_category


def test_keyword_category_mapping() -> None:
    assert map_category("uber") == "Travel"
    assert map_category("Ola") == "Travel"
    assert map_category("fuel") == "Travel"
    assert map_category("petrol") == "Travel"
    assert map_category("Swiggy") == "Food"
    assert map_category("zomato") == "Food"
    assert map_category("restaurant") == "Food"
    assert map_category("Hostinger") == "Software"
    assert map_category("github") == "Software"
    assert map_category("vercel") == "Software"


def test_unknown_merchant_maps_to_other() -> None:
    assert map_category("UnknownVendor") == "Other"


def test_normalize_rejects_unknown_categories() -> None:
    assert normalize_category("Travel") == "Travel"
    assert normalize_category("client expense") == "Client Expense"
    assert normalize_category("NotARealCategory") == "Other"


def test_allowed_categories_are_fixed() -> None:
    assert ALLOWED_CATEGORIES == (
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
