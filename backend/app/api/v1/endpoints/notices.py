import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.session import get_async_db
from app.models.policy import PolicyType
from app.models.renewal_notice import NoticeSource, NoticeStatus, RenewalNotice
from app.schemas.renewal_notice import RenewalNoticeListResponse, RenewalNoticeRead

router = APIRouter(prefix="/notices", tags=["notices"])


def _to_read(notice: RenewalNotice) -> RenewalNoticeRead:
    data = RenewalNoticeRead.model_validate(notice)
    data.has_document = notice.renewal_document is not None
    data.provider_name = notice.provider.provider_name if notice.provider else None
    return data


@router.get("", response_model=RenewalNoticeListResponse)
async def list_notices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    expiry_date_from: Optional[str] = None,
    expiry_date_to: Optional[str] = None,
    insurance_provider_id: Optional[uuid.UUID] = None,
    type_of_policy: Optional[PolicyType] = None,
    notice_status: Optional[NoticeStatus] = None,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    q = select(RenewalNotice).options(selectinload(RenewalNotice.provider))

    if expiry_date_from:
        q = q.where(RenewalNotice.policy_expiry_date >= expiry_date_from)
    if expiry_date_to:
        q = q.where(RenewalNotice.policy_expiry_date <= expiry_date_to)
    if insurance_provider_id:
        q = q.where(RenewalNotice.insurance_provider_id == insurance_provider_id)
    if type_of_policy:
        q = q.where(RenewalNotice.type_of_policy == type_of_policy)
    if notice_status:
        q = q.where(RenewalNotice.status == notice_status)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(RenewalNotice.policy_expiry_date.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    notices = result.scalars().all()

    return RenewalNoticeListResponse(
        items=[_to_read(n) for n in notices],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{notice_id}", response_model=RenewalNoticeRead)
async def get_notice(
    notice_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(RenewalNotice).options(selectinload(RenewalNotice.provider)).where(RenewalNotice.id == notice_id)
    )
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return _to_read(notice)


@router.get("/{notice_id}/document")
async def download_document(
    notice_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    """Stream the renewal document PDF."""
    result = await db.execute(select(RenewalNotice).where(RenewalNotice.id == notice_id))
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    if not notice.renewal_document:
        raise HTTPException(status_code=404, detail="Document not yet available")

    filename = notice.document_filename or f"renewal_{notice.policy_number}.pdf"
    return Response(
        content=notice.renewal_document,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{notice_id}/upload", response_model=RenewalNoticeRead)
async def upload_document(
    notice_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    """Manual upload of a renewal document PDF by an agent."""
    result = await db.execute(
        select(RenewalNotice).options(selectinload(RenewalNotice.provider)).where(RenewalNotice.id == notice_id)
    )
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    if notice.status == NoticeStatus.completed:
        raise HTTPException(status_code=409, detail="Document already uploaded")

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted")

    content = await file.read()
    notice.renewal_document = content
    notice.document_filename = file.filename
    notice.status = NoticeStatus.completed
    notice.source = NoticeSource.manual_upload

    await db.flush()

    # Dispatch notification task
    from app.tasks.notifications import dispatch_notifications_for_notice
    dispatch_notifications_for_notice.delay(str(notice_id))

    await db.refresh(notice, ["provider"])
    return _to_read(notice)


@router.post("/{notice_id}/regenerate", response_model=RenewalNoticeRead)
async def regenerate_notice(
    notice_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    """Manually trigger portal automation for a notice."""
    result = await db.execute(
        select(RenewalNotice).options(selectinload(RenewalNotice.provider)).where(RenewalNotice.id == notice_id)
    )
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    # Reset to pending_automation so the task can run again
    notice.status = NoticeStatus.pending_automation
    notice.renewal_document = None
    notice.document_filename = None
    notice.source = None
    await db.flush()

    from app.tasks.portal import generate_renewal_notice
    generate_renewal_notice.delay(str(notice_id))

    await db.refresh(notice, ["provider"])
    return _to_read(notice)
