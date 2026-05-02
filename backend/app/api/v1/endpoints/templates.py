import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_async_db
from app.models.message_template import MessageTemplate
from app.schemas.message_template import MessageTemplatePreview, MessageTemplateRead, MessageTemplateUpdate

router = APIRouter(prefix="/templates", tags=["templates"])

TEMPLATE_VARS = {"customer_name", "policy_number", "policy_expiry_date"}


def _render(body: str, subject: str | None, preview: MessageTemplatePreview) -> dict:
    replacements = {
        "{{customer_name}}": preview.customer_name,
        "{{policy_number}}": preview.policy_number,
        "{{policy_expiry_date}}": preview.policy_expiry_date,
    }
    rendered_body = body
    rendered_subject = subject or ""
    for placeholder, value in replacements.items():
        rendered_body = rendered_body.replace(placeholder, value)
        rendered_subject = rendered_subject.replace(placeholder, value)
    return {"subject": rendered_subject or None, "body": rendered_body}


@router.get("", response_model=list[MessageTemplateRead])
async def list_templates(
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(MessageTemplate).order_by(MessageTemplate.template_key))
    return [MessageTemplateRead.model_validate(t) for t in result.scalars().all()]


@router.get("/{template_id}", response_model=MessageTemplateRead)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(MessageTemplate).where(MessageTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return MessageTemplateRead.model_validate(template)


@router.patch("/{template_id}", response_model=MessageTemplateRead)
async def update_template(
    template_id: uuid.UUID,
    payload: MessageTemplateUpdate,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(MessageTemplate).where(MessageTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if payload.subject is not None:
        template.subject = payload.subject
    template.body = payload.body

    await db.flush()
    await db.refresh(template)
    return MessageTemplateRead.model_validate(template)


@router.post("/preview")
async def preview_template(
    payload: MessageTemplatePreview,
    db: AsyncSession = Depends(get_async_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.template_key == payload.template_key)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _render(template.body, template.subject, payload)
