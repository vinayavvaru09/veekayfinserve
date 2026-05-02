import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class NotificationChannel(str, enum.Enum):
    whatsapp = "whatsapp"
    email = "email"


class NotificationLanguage(str, enum.Enum):
    en = "en"
    te = "te"


class NotificationStatus(str, enum.Enum):
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


class NotificationLog(UUIDMixin, Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        UniqueConstraint("policy_number", "channel", "days_to_expiry", name="uq_notification_policy_channel_day"),
    )

    renewal_notice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("renewal_notices.id"), nullable=False, index=True
    )
    policy_number: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), nullable=False)
    language: Mapped[NotificationLanguage | None] = mapped_column(Enum(NotificationLanguage), nullable=True)
    days_to_expiry: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    renewal_notice: Mapped["RenewalNotice"] = relationship("RenewalNotice", back_populates="notification_logs")
