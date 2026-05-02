import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.session import get_async_db
from app.models.policy import Policy, PolicyType
from app.schemas.policy import PolicyCreate, PolicyListResponse, PolicyRead, PolicyUpdate

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=PolicyListResponse)
async def list_policies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type_of_policy: Optional[PolicyType] = None,
    insurance_provider_id: Optional[uuid.UUID] = None,
    expiry_date_from: Optional[str] = None,
    expiry_date_to: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    q = select(Policy).options(selectinload(Policy.provider))

    if type_of_policy:
        q = q.where(Policy.type_of_policy == type_of_policy)
    if insurance_provider_id:
        q = q.where(Policy.insurance_provider_id == insurance_provider_id)
    if expiry_date_from:
        q = q.where(Policy.policy_expiry_date >= expiry_date_from)
    if expiry_date_to:
        q = q.where(Policy.policy_expiry_date <= expiry_date_to)
    if search:
        q = q.where(
            Policy.policy_number.ilike(f"%{search}%") | Policy.customer_name.ilike(f"%{search}%")
        )

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(Policy.policy_expiry_date.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    policies = result.scalars().all()

    items = []
    for p in policies:
        data = PolicyRead.model_validate(p)
        data.provider_name = p.provider.provider_name if p.provider else None
        items.append(data)

    return PolicyListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
async def create_policy(
    payload: PolicyCreate,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    existing = await db.execute(select(Policy).where(Policy.policy_number == payload.policy_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Policy number already exists")

    policy = Policy(**payload.model_dump())
    db.add(policy)
    await db.flush()
    await db.refresh(policy, ["provider"])
    data = PolicyRead.model_validate(policy)
    data.provider_name = policy.provider.provider_name if policy.provider else None
    return data


@router.get("/{policy_id}", response_model=PolicyRead)
async def get_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Policy).options(selectinload(Policy.provider)).where(Policy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    data = PolicyRead.model_validate(policy)
    data.provider_name = policy.provider.provider_name if policy.provider else None
    return data


@router.patch("/{policy_id}", response_model=PolicyRead)
async def update_policy(
    policy_id: uuid.UUID,
    payload: PolicyUpdate,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Policy).options(selectinload(Policy.provider)).where(Policy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)

    await db.flush()
    await db.refresh(policy, ["provider"])
    data = PolicyRead.model_validate(policy)
    data.provider_name = policy.provider.provider_name if policy.provider else None
    return data


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.delete(policy)
