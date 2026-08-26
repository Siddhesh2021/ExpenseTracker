from app.parsers.confirmation_parser import parse_confirmation_intent
from app.parsers.edit_parser import parse_edit


def test_parse_save_variants() -> None:
    for text in ("save", "yes", "confirm", "add anyway"):
        parsed = parse_confirmation_intent(text)
        assert parsed is not None
        assert parsed.name == "save"


def test_parse_cancel_variants() -> None:
    for text in ("cancel", "no", "discard"):
        parsed = parse_confirmation_intent(text)
        assert parsed is not None
        assert parsed.name == "cancel"


def test_parse_edit() -> None:
    parsed = parse_confirmation_intent("edit")
    assert parsed is not None
    assert parsed.name == "edit"


def test_unknown_is_not_a_confirmation_command() -> None:
    assert parse_confirmation_intent("₹450 Uber") is None
    assert parse_confirmation_intent("maybe") is None


def test_parse_edit_amount() -> None:
    parsed = parse_edit("change amount to 500")
    assert parsed is not None
    assert parsed.field == "amount"
    assert parsed.value == "500"


def test_parse_edit_category() -> None:
    parsed = parse_edit("change category to Software")
    assert parsed is not None
    assert parsed.field == "category"
    assert parsed.value == "Software"
