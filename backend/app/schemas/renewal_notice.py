import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.policy import PolicyType
from app.models.renewal_notice import NoticeSource, NoticeStatus


class RenewalNoticeRead(BaseModel):
    id: uuid.UUID
    policy_id: uuid.UUID
    policy_number: str
    policy_expiry_date: date
    customer_name: str
    phone_number: Optional[str]
    email: Optional[str]
    type_of_policy: PolicyType
    insurance_provider_id: uuid.UUID
    provider_name: Optional[str] = None  # joined
    status: NoticeStatus
    source: Optional[NoticeSource]
    document_filename: Optional[str]
    has_document: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RenewalNoticeListResponse(BaseModel):
    items: list[RenewalNoticeRead]
    total: int
    page: int
    page_size: int


class RenewalNoticeFilter(BaseModel):
    expiry_date_from: Optional[date] = None
    expiry_date_to: Optional[date] = None
    insurance_provider_id: Optional[uuid.UUID] = None
    type_of_policy: Optional[PolicyType] = None
    status: Optional[NoticeStatus] = None
