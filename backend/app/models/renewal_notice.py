import enum
import uuid

from sqlalchemy import Date, Enum, ForeignKey, LargeBinary, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.policy import PolicyType


class NoticeStatus(str, enum.Enum):
    pending_automation = "pending_automation"
    pending_manual_upload = "pending_manual_upload"
    completed = "completed"
    failed = "failed"


class NoticeSource(str, enum.Enum):
    automated = "automated"
    manual_upload = "manual_upload"
    reused = "reused"


class RenewalNotice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "renewal_notices"
    __table_args__ = (
        UniqueConstraint("policy_number", "policy_expiry_date", name="uq_notice_policy_expiry"),
    )

    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False, index=True
    )
    insurance_provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insurance_providers.id"), nullable=False
    )

    # Denormalized snapshot fields
    policy_number: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    policy_expiry_date: Mapped[str] = mapped_column(Date, nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(Text, nullable=False)
    date_of_birth: Mapped[str | None] = mapped_column(Date, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    type_of_policy: Mapped[PolicyType] = mapped_column(Enum(PolicyType), nullable=False)
    hold_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    renewed_date: Mapped[str | None] = mapped_column(Date, nullable=True)

    # Document
    renewal_document: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    document_filename: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[NoticeStatus] = mapped_column(
        Enum(NoticeStatus), nullable=False, default=NoticeStatus.pending_automation, index=True
    )
    source: Mapped[NoticeSource | None] = mapped_column(Enum(NoticeSource), nullable=True)

    # Relationships
    policy: Mapped["Policy"] = relationship("Policy", back_populates="renewal_notices")
    provider: Mapped["InsuranceProvider"] = relationship("InsuranceProvider", back_populates="renewal_notices")
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        "NotificationLog", back_populates="renewal_notice"
    )
