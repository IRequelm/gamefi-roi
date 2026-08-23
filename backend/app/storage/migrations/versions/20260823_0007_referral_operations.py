"""Add referral operations fields and tasks.

Revision ID: 20260823_0007
Revises: 20260823_0006
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa

revision = "20260823_0007"
down_revision = "20260823_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("referral_programs", sa.Column("official_url", sa.String(length=2048), nullable=True))
    op.add_column("referral_programs", sa.Column("referral_url", sa.String(length=2048), nullable=True))
    op.add_column("referral_programs", sa.Column("referral_code", sa.String(length=255), nullable=True))
    op.add_column("referral_programs", sa.Column("referral_url_template", sa.String(length=2048), nullable=True))
    op.add_column("referral_programs", sa.Column("program_type", sa.String(length=128), nullable=True))
    op.add_column("referral_programs", sa.Column("commission_description", sa.String(length=2048), nullable=True))
    op.add_column("referral_programs", sa.Column("eligibility_notes", sa.String(length=2048), nullable=True))
    op.add_column("referral_programs", sa.Column("geographic_restrictions", sa.String(length=1024), nullable=True))
    op.add_column("referral_programs", sa.Column("evidence_url", sa.String(length=2048), nullable=True))
    op.add_column("referral_programs", sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("referral_programs", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("referral_programs", sa.Column("operator_notes", sa.String(length=4096), nullable=True))

    op.add_column("revenue_attributions", sa.Column("settlement_reference_id", sa.String(length=255), nullable=True))
    op.add_column("revenue_attributions", sa.Column("notes", sa.String(length=4096), nullable=True))

    op.create_table(
        "referral_tasks",
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("opportunity_id", sa.String(length=255), nullable=False),
        sa.Column("destination_slug", sa.String(length=255), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=2048), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(length=4096), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("task_id", name=op.f("pk_referral_tasks")),
    )
    op.create_index(op.f("ix_referral_tasks_destination_slug"), "referral_tasks", ["destination_slug"])
    op.create_index(op.f("ix_referral_tasks_due_at"), "referral_tasks", ["due_at"])
    op.create_index(op.f("ix_referral_tasks_opportunity_id"), "referral_tasks", ["opportunity_id"])
    op.create_index(op.f("ix_referral_tasks_status"), "referral_tasks", ["status"])
    op.create_index(op.f("ix_referral_tasks_task_type"), "referral_tasks", ["task_type"])


def downgrade() -> None:
    op.drop_index(op.f("ix_referral_tasks_task_type"), table_name="referral_tasks")
    op.drop_index(op.f("ix_referral_tasks_status"), table_name="referral_tasks")
    op.drop_index(op.f("ix_referral_tasks_opportunity_id"), table_name="referral_tasks")
    op.drop_index(op.f("ix_referral_tasks_due_at"), table_name="referral_tasks")
    op.drop_index(op.f("ix_referral_tasks_destination_slug"), table_name="referral_tasks")
    op.drop_table("referral_tasks")

    op.drop_column("revenue_attributions", "notes")
    op.drop_column("revenue_attributions", "settlement_reference_id")

    op.drop_column("referral_programs", "operator_notes")
    op.drop_column("referral_programs", "expires_at")
    op.drop_column("referral_programs", "applied_at")
    op.drop_column("referral_programs", "evidence_url")
    op.drop_column("referral_programs", "geographic_restrictions")
    op.drop_column("referral_programs", "eligibility_notes")
    op.drop_column("referral_programs", "commission_description")
    op.drop_column("referral_programs", "program_type")
    op.drop_column("referral_programs", "referral_url_template")
    op.drop_column("referral_programs", "referral_code")
    op.drop_column("referral_programs", "referral_url")
    op.drop_column("referral_programs", "official_url")
