from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.ai.base import AIProvider
from app.api.deps import get_ai_provider_optional, get_whatsapp_service
from app.db.database import get_session_factory
from app.db.models import Expense, ProcessedWhatsAppMessage, User
from app.main import create_app
from app.schemas.expense import ExpenseExtraction, ExtractionContext
from app.services.whatsapp_service import WhatsAppAPIError
from tests.whatsapp_payloads import button_payload, image_payload, status_payload, text_payload


class FakeWhatsApp:
    def __init__(self) -> None:
        self.texts: list[tuple[str, str]] = []
        self.interactives: list[tuple[str, str, list[tuple[str, str]]]] = []
        self.fail_interactive = False

    def send_text_message(self, to: str, body: str) -> None:
        self.texts.append((to, body))

    def send_interactive_message(self, to: str, body: str, buttons: list[tuple[str, str]]) -> None:
        if self.fail_interactive:
            raise WhatsAppAPIError("interactive failed")
        self.interactives.append((to, body, buttons))


class SilentAI(AIProvider):
    def extract_expense(self, message: str, context: ExtractionContext) -> ExpenseExtraction:
        raise AssertionError("Gemini should not be called for this test")


@pytest.fixture
def fake_wa() -> FakeWhatsApp:
    return FakeWhatsApp()


@pytest.fixture
def wa_client(db_session, fake_wa: FakeWhatsApp) -> Generator[TestClient, None, None]:
    app = create_app()
    app.dependency_overrides[get_whatsapp_service] = lambda: fake_wa
    app.dependency_overrides[get_ai_provider_optional] = lambda: SilentAI()
    with TestClient(app) as test_client:
        yield test_client


def test_webhook_verification_success(wa_client: TestClient) -> None:
    response = wa_client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "test-verify-token", "hub.challenge": "challenge-123"},
    )
    assert response.status_code == 200
    assert response.text == "challenge-123"


def test_webhook_verification_rejects_bad_token(wa_client: TestClient) -> None:
    response = wa_client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "challenge-123"},
    )
    assert response.status_code == 403


def test_text_expense_is_saved_and_replied(wa_client: TestClient, fake_wa: FakeWhatsApp) -> None:
    response = wa_client.post("/webhook", json=text_payload("wamid.exp1", "919111111111", "₹450 Uber"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake_wa.texts
    assert "Expense added" in fake_wa.texts[0][1]
    session = get_session_factory()()
    try:
        assert session.scalar(select(func.count()).select_from(Expense)) == 1
        user = session.scalar(select(User).where(User.whatsapp_number == "919111111111"))
        assert user is not None
        assert user.name == "Sid"
    finally:
        session.close()


def test_help_command(wa_client: TestClient, fake_wa: FakeWhatsApp) -> None:
    wa_client.post("/webhook", json=text_payload("wamid.help", "919111111111", "/help"))
    assert fake_wa.texts
    assert "Welcome to ExpenseTracker" in fake_wa.texts[0][1]


def test_greeting_onboards_user(wa_client: TestClient, fake_wa: FakeWhatsApp) -> None:
    wa_client.post("/webhook", json=text_payload("wamid.hi", "919222222222", "Hi"))
    assert "Welcome to ExpenseTracker" in fake_wa.texts[0][1]
    session = get_session_factory()()
    try:
        assert session.scalar(select(User).where(User.whatsapp_number == "919222222222")) is not None
    finally:
        session.close()


def test_placeholder_commands(wa_client: TestClient, fake_wa: FakeWhatsApp) -> None:
    wa_client.post("/webhook", json=text_payload("wamid.sum", "919111111111", "/summary"))
    assert "coming soon" in fake_wa.texts[-1][1]
    wa_client.post("/webhook", json=text_payload("wamid.ex", "919111111111", "/expenses"))
    assert "coming soon" in fake_wa.texts[-1][1]
    wa_client.post("/webhook", json=text_payload("wamid.exp", "919111111111", "/export"))
    assert "coming soon" in fake_wa.texts[-1][1]


def test_unsupported_media(wa_client: TestClient, fake_wa: FakeWhatsApp) -> None:
    wa_client.post("/webhook", json=image_payload("wamid.img1", "919111111111"))
    assert fake_wa.texts
    assert "Receipt scanning is coming in Phase 2" in fake_wa.texts[0][1]


def test_idempotency_skips_duplicate_message_id(wa_client: TestClient, fake_wa: FakeWhatsApp) -> None:
    payload = text_payload("wamid.same", "919111111111", "₹450 Uber")
    wa_client.post("/webhook", json=payload)
    wa_client.post("/webhook", json=payload)
    assert len(fake_wa.texts) == 1
    session = get_session_factory()()
    try:
        assert session.scalar(select(func.count()).select_from(Expense)) == 1
        assert session.scalar(select(func.count()).select_from(ProcessedWhatsAppMessage)) == 1
    finally:
        session.close()


def test_status_webhook_is_ignored(wa_client: TestClient, fake_wa: FakeWhatsApp) -> None:
    response = wa_client.post("/webhook", json=status_payload())
    assert response.status_code == 200
    assert fake_wa.texts == []
    assert fake_wa.interactives == []


def test_confirmation_uses_interactive_buttons(wa_client: TestClient, fake_wa: FakeWhatsApp, db_session) -> None:
    class HostingAI(AIProvider):
        def extract_expense(self, message: str, context: ExtractionContext) -> ExpenseExtraction:
            from datetime import date
            from decimal import Decimal

            return ExpenseExtraction(
                amount=Decimal("1200"),
                currency="INR",
                merchant="Hosting",
                category="Software",
                expense_date=date(2026, 8, 26),
                client="Acme",
                needs_confirmation=True,
            )

    wa_client.app.dependency_overrides[get_ai_provider_optional] = lambda: HostingAI()
    wa_client.post("/webhook", json=text_payload("wamid.complex", "919333333333", "Spent ₹1200 on hosting for Acme yesterday"))
    assert fake_wa.interactives
    assert fake_wa.interactives[0][1].find("Save this expense?") != -1
    ids = [button[0] for button in fake_wa.interactives[0][2]]
    assert ids == ["save", "edit", "cancel"]
    session = get_session_factory()()
    try:
        assert session.scalar(select(func.count()).select_from(Expense)) == 0
    finally:
        session.close()

    wa_client.post("/webhook", json=button_payload("wamid.savebtn", "919333333333", "save", "Save"))
    assert any("Expense added" in body for _, body in fake_wa.texts)
    session = get_session_factory()()
    try:
        assert session.scalar(select(func.count()).select_from(Expense)) == 1
    finally:
        session.close()


def test_interactive_failure_falls_back_to_text(wa_client: TestClient, fake_wa: FakeWhatsApp) -> None:
    class HostingAI(AIProvider):
        def extract_expense(self, message: str, context: ExtractionContext) -> ExpenseExtraction:
            from datetime import date
            from decimal import Decimal

            return ExpenseExtraction(
                amount=Decimal("1200"),
                currency="INR",
                merchant="Hosting",
                category="Software",
                expense_date=date(2026, 8, 26),
                needs_confirmation=True,
            )

    fake_wa.fail_interactive = True
    wa_client.app.dependency_overrides[get_ai_provider_optional] = lambda: HostingAI()
    wa_client.post("/webhook", json=text_payload("wamid.fb", "919444444444", "Spent ₹1200 on hosting for Acme yesterday"))
    assert fake_wa.interactives == []
    assert fake_wa.texts
    assert "save, edit, or cancel" in fake_wa.texts[0][1].lower()
