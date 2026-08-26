from app.parsers.whatsapp_parser import parse_incoming_messages
from tests.whatsapp_payloads import button_payload, image_payload, status_payload, text_payload


def test_parse_text_message() -> None:
    messages = parse_incoming_messages(text_payload("wamid.1", "919999999999", "₹450 Uber"))
    assert len(messages) == 1
    assert messages[0].message_id == "wamid.1"
    assert messages[0].sender == "919999999999"
    assert messages[0].message_type == "text"
    assert messages[0].text == "₹450 Uber"
    assert messages[0].contact_name == "Sid"


def test_parse_image_message() -> None:
    messages = parse_incoming_messages(image_payload("wamid.img", "919999999999"))
    assert messages[0].message_type == "image"
    assert messages[0].text is None


def test_parse_button_reply() -> None:
    messages = parse_incoming_messages(button_payload("wamid.btn", "919999999999", "save", "Save"))
    assert messages[0].text == "save"


def test_status_events_are_ignored() -> None:
    assert parse_incoming_messages(status_payload()) == []
