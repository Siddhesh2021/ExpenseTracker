from datetime import date
from decimal import Decimal

from app.utils.dates import today as today_in_timezone


def format_money(amount: Decimal, currency: str = "INR") -> str:
    quantized = amount.quantize(Decimal("0.01"))
    if quantized == quantized.to_integral():
        formatted = f"{int(quantized):,}"
    else:
        formatted = f"{quantized:,.2f}"
    if currency.upper() == "INR":
        return f"₹{formatted}"
    return f"{currency} {formatted}"


def format_expense_date(expense_date: date | None, timezone_name: str = "Asia/Kolkata") -> str:
    if expense_date is None:
        return "Today"
    if expense_date == today_in_timezone(timezone_name):
        return "Today"
    return expense_date.strftime("%d %b").lstrip("0")
