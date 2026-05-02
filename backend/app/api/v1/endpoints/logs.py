from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_async_db
from app.models.processing_log import ProcessingLog
from app.schemas.processing_log import ProcessingLogListResponse, ProcessingLogRead

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=ProcessingLogListResponse)
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    run_date_from: Optional[str] = None,
    run_date_to: Optional[str] = None,
    action: Optional[str] = None,
    policy_number: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    q = select(ProcessingLog)

    if run_date_from:
        q = q.where(ProcessingLog.run_date >= run_date_from)
    if run_date_to:
        q = q.where(ProcessingLog.run_date <= run_date_to)
    if action:
        q = q.where(ProcessingLog.action == action)
    if policy_number:
        q = q.where(ProcessingLog.policy_number.ilike(f"%{policy_number}%"))

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(ProcessingLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    logs = result.scalars().all()

    return ProcessingLogListResponse(
        items=[ProcessingLogRead.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )
