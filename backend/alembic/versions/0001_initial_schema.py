"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enums ---
    policy_type = postgresql.ENUM("Motor", "Life", "Medical", name="policytype", create_type=True)
    notice_status = postgresql.ENUM(
        "pending_automation", "pending_manual_upload", "completed", "failed",
        name="noticestatus", create_type=True,
    )
    notice_source = postgresql.ENUM("automated", "manual_upload", "reused", name="noticesource", create_type=True)
    notification_channel = postgresql.ENUM("whatsapp", "email", name="notificationchannel", create_type=True)
    notification_language = postgresql.ENUM("en", "te", name="notificationlanguage", create_type=True)
    notification_status = postgresql.ENUM("sent", "failed", "skipped", name="notificationstatus", create_type=True)

    for e in [policy_type, notice_status, notice_source, notification_channel, notification_language, notification_status]:
        e.create(op.get_bind(), checkfirst=True)

    # --- insurance_providers ---
    op.create_table(
        "insurance_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_name", sa.Text, nullable=False, unique=True),
        sa.Column("portal_url", sa.Text, nullable=False),
        sa.Column("login_credentials_encrypted", sa.Text, nullable=False),
        sa.Column("additional_auth_encrypted", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- policies ---
    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_name", sa.Text, nullable=False),
        sa.Column("policy_number", sa.Text, nullable=False, unique=True),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("phone_number", sa.Text, nullable=True),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column("type_of_policy", sa.Enum("Motor", "Life", "Medical", name="policytype"), nullable=False),
        sa.Column("insurance_provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("insurance_providers.id"), nullable=False),
        sa.Column("policy_expiry_date", sa.Date, nullable=False),
        sa.Column("hold_date", sa.Date, nullable=True),
        sa.Column("renewed_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_policies_policy_number", "policies", ["policy_number"])
    op.create_index("ix_policies_policy_expiry_date", "policies", ["policy_expiry_date"])

    # --- renewal_notices ---
    op.create_table(
        "renewal_notices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("policies.id"), nullable=False),
        sa.Column("insurance_provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("insurance_providers.id"), nullable=False),
        sa.Column("policy_number", sa.Text, nullable=False),
        sa.Column("policy_expiry_date", sa.Date, nullable=False),
        sa.Column("customer_name", sa.Text, nullable=False),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("phone_number", sa.Text, nullable=True),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column("type_of_policy", sa.Enum("Motor", "Life", "Medical", name="policytype"), nullable=False),
        sa.Column("hold_date", sa.Date, nullable=True),
        sa.Column("renewed_date", sa.Date, nullable=True),
        sa.Column("renewal_document", sa.LargeBinary, nullable=True),
        sa.Column("document_filename", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("pending_automation", "pending_manual_upload", "completed", "failed", name="noticestatus"), nullable=False),
        sa.Column("source", sa.Enum("automated", "manual_upload", "reused", name="noticesource"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("policy_number", "policy_expiry_date", name="uq_notice_policy_expiry"),
    )
    op.create_index("ix_renewal_notices_policy_id", "renewal_notices", ["policy_id"])
    op.create_index("ix_renewal_notices_policy_number", "renewal_notices", ["policy_number"])
    op.create_index("ix_renewal_notices_policy_expiry_date", "renewal_notices", ["policy_expiry_date"])
    op.create_index("ix_renewal_notices_status", "renewal_notices", ["status"])

    # --- notification_logs ---
    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("renewal_notice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("renewal_notices.id"), nullable=False),
        sa.Column("policy_number", sa.Text, nullable=False),
        sa.Column("channel", sa.Enum("whatsapp", "email", name="notificationchannel"), nullable=False),
        sa.Column("language", sa.Enum("en", "te", name="notificationlanguage"), nullable=True),
        sa.Column("days_to_expiry", sa.Integer, nullable=False),
        sa.Column("status", sa.Enum("sent", "failed", "skipped", name="notificationstatus"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.UniqueConstraint("policy_number", "channel", "days_to_expiry", name="uq_notification_policy_channel_day"),
    )
    op.create_index("ix_notification_logs_renewal_notice_id", "notification_logs", ["renewal_notice_id"])
    op.create_index("ix_notification_logs_policy_number", "notification_logs", ["policy_number"])

    # --- processing_logs ---
    op.create_table(
        "processing_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_date", sa.Date, nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("policies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("policy_number", sa.Text, nullable=True),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_processing_logs_run_date", "processing_logs", ["run_date"])
    op.create_index("ix_processing_logs_policy_number", "processing_logs", ["policy_number"])
    op.create_index("ix_processing_logs_action", "processing_logs", ["action"])

    # --- message_templates ---
    op.create_table(
        "message_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel", sa.Enum("whatsapp", "email", name="notificationchannel"), nullable=False),
        sa.Column("language", sa.Enum("en", "te", name="notificationlanguage"), nullable=True),
        sa.Column("template_key", sa.Text, nullable=False, unique=True),
        sa.Column("subject", sa.Text, nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- Seed default message templates ---
    op.execute("""
        INSERT INTO message_templates (id, channel, language, template_key, subject, body, created_at, updated_at)
        VALUES
        (
            gen_random_uuid(), 'whatsapp', 'en', 'whatsapp_renewal_en', NULL,
            'Dear {{customer_name}}, your insurance policy {{policy_number}} is due for renewal on {{policy_expiry_date}}. Please find the renewal notice attached. Contact us to proceed.',
            NOW(), NOW()
        ),
        (
            gen_random_uuid(), 'whatsapp', 'te', 'whatsapp_renewal_te', NULL,
            'ప్రియమైన {{customer_name}}, మీ బీమా పాలసీ {{policy_number}} {{policy_expiry_date}} న పునరుద్ధరణకు సిద్ధంగా ఉంది. దయచేసి జతచేసిన పునరుద్ధరణ నోటీసును చూడండి.',
            NOW(), NOW()
        ),
        (
            gen_random_uuid(), 'email', NULL, 'email_renewal', 'Insurance Renewal Notice — Policy {{policy_number}}',
            'Dear {{customer_name}},\n\nYour insurance policy {{policy_number}} is due for renewal on {{policy_expiry_date}}.\n\nPlease find the renewal notice document attached to this email.\n\nFor assistance, contact Veekay Finserve.\n\nRegards,\nVeekay Finserve Team',
            NOW(), NOW()
        )
    """)


def downgrade() -> None:
    op.drop_table("message_templates")
    op.drop_table("processing_logs")
    op.drop_table("notification_logs")
    op.drop_table("renewal_notices")
    op.drop_table("policies")
    op.drop_table("insurance_providers")

    for name in ["policytype", "noticestatus", "noticesource", "notificationchannel", "notificationlanguage", "notificationstatus"]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
