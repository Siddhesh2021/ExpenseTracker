from pydantic import BaseModel, ConfigDict


class IncomingWhatsAppMessage(BaseModel):
    message_id: str
    sender: str
    message_type: str
    text: str | None = None
    contact_name: str | None = None

    model_config = ConfigDict(frozen=True)


class WhatsAppButton(BaseModel):
    id: str
    title: str
