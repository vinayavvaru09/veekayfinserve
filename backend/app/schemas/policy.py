import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.policy import PolicyType


class PolicyBase(BaseModel):
    customer_name: str
    policy_number: str
    date_of_birth: Optional[date] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    type_of_policy: PolicyType
    insurance_provider_id: uuid.UUID
    policy_expiry_date: date
    hold_date: Optional[date] = None
    renewed_date: Optional[date] = None


class PolicyCreate(PolicyBase):
    pass


class PolicyUpdate(BaseModel):
    customer_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    type_of_policy: Optional[PolicyType] = None
    insurance_provider_id: Optional[uuid.UUID] = None
    policy_expiry_date: Optional[date] = None
    hold_date: Optional[date] = None
    renewed_date: Optional[date] = None


class PolicyRead(PolicyBase):
    id: uuid.UUID
    provider_name: Optional[str] = None  # joined from provider

    model_config = {"from_attributes": True}


class PolicyListResponse(BaseModel):
    items: list[PolicyRead]
    total: int
    page: int
    page_size: int
