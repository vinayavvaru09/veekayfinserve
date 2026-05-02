import enum

from sqlalchemy import Enum, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.notification_log import NotificationChannel, NotificationLanguage


class MessageTemplate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "message_templates"

    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), nullable=False)
    language: Mapped[NotificationLanguage | None] = mapped_column(Enum(NotificationLanguage), nullable=True)
    template_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)  # email only
    body: Mapped[str] = mapped_column(Text, nullable=False)
