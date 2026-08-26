from app.core.categories import ALLOWED_CATEGORIES

SYSTEM_PROMPT = """You extract a single expense from a user's WhatsApp message.

Return JSON only. No markdown. No commentary.

Rules:
- Use only these categories: {categories}
- If the category is uncertain, use "Other". Never invent a new category.
- Do not invent information. If a field is unknown, return null.
- Never invent an amount. The amount must appear in the user message.
- Never invent a merchant. If no merchant is stated, return null.
- amount must be a number (no currency symbols). Use null if missing.
- expense_date must be ISO format YYYY-MM-DD, or null.
- Interpret relative dates using the provided today/timezone context.
- currency should be INR when the user uses ₹, Rs, INR, or no currency is specified.
- client and project are optional; use null if not mentioned.
- description should be a short factual summary or null.
- needs_confirmation is true when the message is ambiguous, missing merchant, or contains more than one expense.
- If the message contains multiple expenses, extract only the first amount mentioned and set needs_confirmation to true.
"""

USER_PROMPT_TEMPLATE = """Today: {today}
Timezone: {timezone}
Default currency: {currency}

User message:
{message}
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT.format(categories=", ".join(ALLOWED_CATEGORIES))


def build_user_prompt(message: str, today: str, timezone: str, currency: str) -> str:
    return USER_PROMPT_TEMPLATE.format(
        today=today,
        timezone=timezone,
        currency=currency,
        message=message.strip(),
    )
