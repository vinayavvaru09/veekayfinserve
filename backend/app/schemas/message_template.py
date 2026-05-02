import uuid
from typing import Optional

from pydantic import BaseModel

from app.models.notification_log import NotificationChannel, NotificationLanguage


class MessageTemplateRead(BaseModel):
    id: uuid.UUID
    channel: NotificationChannel
    language: Optional[NotificationLanguage]
    template_key: str
    subject: Optional[str]
    body: str

    model_config = {"from_attributes": True}


class MessageTemplateUpdate(BaseModel):
    subject: Optional[str] = None
    body: str


class MessageTemplatePreview(BaseModel):
    template_key: str
    customer_name: str = "Sample Customer"
    policy_number: str = "POL-000001"
    policy_expiry_date: str = "2024-12-31"
