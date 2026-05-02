import uuid
from typing import Optional

from pydantic import BaseModel, HttpUrl


class ProviderBase(BaseModel):
    provider_name: str
    portal_url: str


class ProviderCreate(ProviderBase):
    login_credentials: dict  # plaintext JSON — encrypted before storage
    additional_auth_details: Optional[dict] = None


class ProviderUpdate(BaseModel):
    provider_name: Optional[str] = None
    portal_url: Optional[str] = None
    login_credentials: Optional[dict] = None
    additional_auth_details: Optional[dict] = None


class ProviderRead(ProviderBase):
    id: uuid.UUID
    # Credentials are never returned in plaintext

    model_config = {"from_attributes": True}


class ProviderListResponse(BaseModel):
    items: list[ProviderRead]
    total: int
