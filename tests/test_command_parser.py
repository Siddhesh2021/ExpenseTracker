from app.parsers.command_parser import parse_command


def test_parse_help_command() -> None:
    parsed = parse_command("/help")
    assert parsed is not None
    assert parsed.name == "help"
    assert parsed.argument is None


def test_parse_summary_command() -> None:
    assert parse_command("  /summary  ").name == "summary"


def test_parse_export_command() -> None:
    assert parse_command("/export").name == "export"


def test_parse_expenses_with_filter() -> None:
    parsed = parse_command("/expenses today")
    assert parsed is not None
    assert parsed.name == "expenses"
    assert parsed.argument == "today"


def test_parse_expenses_this_month() -> None:
    parsed = parse_command("/expenses this month")
    assert parsed is not None
    assert parsed.argument == "this month"


def test_plain_text_is_not_a_command() -> None:
    assert parse_command("₹450 Uber") is None
    assert parse_command("help") is None


def test_unknown_slash_command_is_ignored() -> None:
    assert parse_command("/unknown") is None
