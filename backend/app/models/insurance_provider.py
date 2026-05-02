import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class InsuranceProvider(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "insurance_providers"

    provider_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    portal_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Stored as Fernet-encrypted JSON string
    login_credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional extra auth details (also encrypted)
    additional_auth_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    policies: Mapped[list["Policy"]] = relationship("Policy", back_populates="provider")
    renewal_notices: Mapped[list["RenewalNotice"]] = relationship("RenewalNotice", back_populates="provider")
