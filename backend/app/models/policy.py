import enum
import uuid

from sqlalchemy import Date, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class PolicyType(str, enum.Enum):
    Motor = "Motor"
    Life = "Life"
    Medical = "Medical"


class Policy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "policies"

    customer_name: Mapped[str] = mapped_column(Text, nullable=False)
    policy_number: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    date_of_birth: Mapped[str | None] = mapped_column(Date, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    type_of_policy: Mapped[PolicyType] = mapped_column(Enum(PolicyType), nullable=False)
    insurance_provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insurance_providers.id"), nullable=False
    )
    policy_expiry_date: Mapped[str] = mapped_column(Date, nullable=False, index=True)
    hold_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    renewed_date: Mapped[str | None] = mapped_column(Date, nullable=True)

    provider: Mapped["InsuranceProvider"] = relationship("InsuranceProvider", back_populates="policies")
    renewal_notices: Mapped[list["RenewalNotice"]] = relationship("RenewalNotice", back_populates="policy")
