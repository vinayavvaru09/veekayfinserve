import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class ProcessingLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "processing_logs"

    run_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="SET NULL"), nullable=True
    )
    policy_number: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    action: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
