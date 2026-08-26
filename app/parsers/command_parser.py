from dataclasses import dataclass

COMMANDS = frozenset({"help", "summary", "expenses", "export"})
HISTORY_FILTERS = frozenset({"today", "this week", "this month"})


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    argument: str | None = None


def parse_command(text: str) -> ParsedCommand | None:
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    parts = stripped[1:].split(None, 1)
    if not parts:
        return None
    name = parts[0].lower()
    if name not in COMMANDS:
        return None
    argument = parts[1].strip().lower() if len(parts) > 1 else None
    if argument == "":
        argument = None
    if name == "expenses" and argument is not None and argument not in HISTORY_FILTERS:
        return ParsedCommand(name=name, argument=None)
    return ParsedCommand(name=name, argument=argument)
