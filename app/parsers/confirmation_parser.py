from dataclasses import dataclass

SAVE_PHRASES = frozenset(
    {
        "save",
        "yes",
        "y",
        "confirm",
        "ok",
        "okay",
        "add",
        "add anyway",
    }
)
CANCEL_PHRASES = frozenset({"cancel", "no", "n", "discard"})
EDIT_PHRASES = frozenset({"edit"})


@dataclass(frozen=True)
class ConfirmationIntent:
    name: str


def parse_confirmation_intent(text: str) -> ConfirmationIntent | None:
    cleaned = " ".join(text.strip().lower().split())
    if not cleaned:
        return None
    if cleaned in SAVE_PHRASES:
        return ConfirmationIntent("save")
    if cleaned in CANCEL_PHRASES:
        return ConfirmationIntent("cancel")
    if cleaned in EDIT_PHRASES:
        return ConfirmationIntent("edit")
    return None
