from types import SimpleNamespace

import httpx
import pytest

from app.core.config import get_settings
from app.services.whatsapp_service import WhatsAppAPIError, WhatsAppService


class FakeHttpx:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict] = []

    def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        if self.error is not None:
            raise self.error
        return SimpleNamespace(raise_for_status=lambda: None)


def test_send_text_message_posts_to_graph() -> None:
    http = FakeHttpx()
    service = WhatsAppService(client=http)
    service.send_text_message("919999999999", "hello")

    assert len(http.calls) == 1
    call = http.calls[0]
    settings = get_settings()
    assert settings.whatsapp_phone_number_id in call["url"]
    assert settings.whatsapp_api_version in call["url"]
    assert call["headers"]["Authorization"].startswith("Bearer ")
    assert call["json"]["to"] == "919999999999"
    assert call["json"]["type"] == "text"
    assert call["json"]["text"]["body"] == "hello"


def test_send_interactive_message_includes_buttons() -> None:
    http = FakeHttpx()
    service = WhatsAppService(client=http)
    service.send_interactive_message("919999999999", "Save this expense?", [("save", "Save"), ("edit", "Edit"), ("cancel", "Cancel")])

    call = http.calls[0]
    assert call["json"]["type"] == "interactive"
    buttons = call["json"]["interactive"]["action"]["buttons"]
    assert [item["reply"]["id"] for item in buttons] == ["save", "edit", "cancel"]


def test_whatsapp_http_error_is_wrapped() -> None:
    http = FakeHttpx(error=httpx.ConnectError("boom"))
    service = WhatsAppService(client=http)
    with pytest.raises(WhatsAppAPIError):
        service.send_text_message("919999999999", "hello")
