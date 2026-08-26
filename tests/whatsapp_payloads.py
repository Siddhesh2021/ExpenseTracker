def text_payload(message_id: str, sender: str, body: str, name: str = "Sid") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [{"profile": {"name": name}, "wa_id": sender}],
                            "messages": [
                                {
                                    "from": sender,
                                    "id": message_id,
                                    "timestamp": "1756272000",
                                    "type": "text",
                                    "text": {"body": body},
                                }
                            ],
                        },
                    }
                ]
            }
        ],
    }


def image_payload(message_id: str, sender: str) -> dict:
    payload = text_payload(message_id, sender, "ignored")
    payload["entry"][0]["changes"][0]["value"]["messages"][0] = {
        "from": sender,
        "id": message_id,
        "timestamp": "1756272000",
        "type": "image",
        "image": {"id": "media-1", "mime_type": "image/jpeg"},
    }
    return payload


def button_payload(message_id: str, sender: str, button_id: str, title: str) -> dict:
    payload = text_payload(message_id, sender, "ignored")
    payload["entry"][0]["changes"][0]["value"]["messages"][0] = {
        "from": sender,
        "id": message_id,
        "timestamp": "1756272000",
        "type": "interactive",
        "interactive": {"type": "button_reply", "button_reply": {"id": button_id, "title": title}},
    }
    return payload


def status_payload() -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "statuses": [{"id": "wamid.status", "status": "delivered"}],
                        },
                    }
                ]
            }
        ],
    }
