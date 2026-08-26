import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

UNSUPPORTED_MEDIA_REPLY = (
    "Currently I support text expenses. Receipt scanning is coming in Phase 2."
)


class WhatsAppAPIError(Exception):
    pass


class WhatsAppService:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._settings = get_settings()
        self._client = client or httpx.Client(timeout=15.0)

    def send_text_message(self, to: str, body: str) -> None:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        self._post(payload)

    def send_interactive_message(self, to: str, body: str, buttons: list[tuple[str, str]]) -> None:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": button_id, "title": title[:20]}}
                        for button_id, title in buttons[:3]
                    ]
                },
            },
        }
        self._post(payload)

    def _post(self, payload: dict) -> None:
        url = (
            f"https://graph.facebook.com/{self._settings.whatsapp_api_version}"
            f"/{self._settings.whatsapp_phone_number_id}/messages"
        )
        headers = {
            "Authorization": f"Bearer {self._settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }
        try:
            response = self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("whatsapp_api_failed")
            raise WhatsAppAPIError("WhatsApp API request failed") from exc
