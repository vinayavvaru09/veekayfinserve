import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ProcessingLogRead(BaseModel):
    id: uuid.UUID
    run_date: date
    policy_id: Optional[uuid.UUID]
    policy_number: Optional[str]
    action: str
    detail: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ProcessingLogListResponse(BaseModel):
    items: list[ProcessingLogRead]
    total: int
    page: int
    page_size: int
