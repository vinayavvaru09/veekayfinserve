import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_credentials, get_current_user
from app.db.session import get_async_db
from app.models.insurance_provider import InsuranceProvider
from app.schemas.provider import ProviderCreate, ProviderListResponse, ProviderRead, ProviderUpdate

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=ProviderListResponse)
async def list_providers(
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(InsuranceProvider).order_by(InsuranceProvider.provider_name))
    providers = result.scalars().all()
    total_result = await db.execute(select(func.count(InsuranceProvider.id)))
    total = total_result.scalar_one()
    return ProviderListResponse(items=[ProviderRead.model_validate(p) for p in providers], total=total)


@router.post("", response_model=ProviderRead, status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: ProviderCreate,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    existing = await db.execute(
        select(InsuranceProvider).where(InsuranceProvider.provider_name == payload.provider_name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Provider name already exists")

    provider = InsuranceProvider(
        provider_name=payload.provider_name,
        portal_url=payload.portal_url,
        login_credentials_encrypted=encrypt_credentials(json.dumps(payload.login_credentials)),
        additional_auth_encrypted=(
            encrypt_credentials(json.dumps(payload.additional_auth_details))
            if payload.additional_auth_details
            else None
        ),
    )
    db.add(provider)
    await db.flush()
    await db.refresh(provider)
    return ProviderRead.model_validate(provider)


@router.get("/{provider_id}", response_model=ProviderRead)
async def get_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(InsuranceProvider).where(InsuranceProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderRead.model_validate(provider)


@router.patch("/{provider_id}", response_model=ProviderRead)
async def update_provider(
    provider_id: uuid.UUID,
    payload: ProviderUpdate,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(InsuranceProvider).where(InsuranceProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if payload.provider_name is not None:
        provider.provider_name = payload.provider_name
    if payload.portal_url is not None:
        provider.portal_url = payload.portal_url
    if payload.login_credentials is not None:
        provider.login_credentials_encrypted = encrypt_credentials(json.dumps(payload.login_credentials))
    if payload.additional_auth_details is not None:
        provider.additional_auth_encrypted = encrypt_credentials(json.dumps(payload.additional_auth_details))

    await db.flush()
    await db.refresh(provider)
    return ProviderRead.model_validate(provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(InsuranceProvider).where(InsuranceProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)
