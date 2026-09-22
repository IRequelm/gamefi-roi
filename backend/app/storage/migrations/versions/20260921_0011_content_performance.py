"""Add source-backed X and YouTube content performance records."""

from alembic import op
import sqlalchemy as sa


revision = "20260921_0011"
down_revision = "20260920_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_performance_records",
        sa.Column("performance_id", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("content_id", sa.String(length=255), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("engagements", sa.Integer(), nullable=True),
        sa.Column("link_clicks", sa.Integer(), nullable=True),
        sa.Column("profile_visits", sa.Integer(), nullable=True),
        sa.Column("followers_gained", sa.Integer(), nullable=True),
        sa.Column("subscribers_gained", sa.Integer(), nullable=True),
        sa.Column("average_retention_percent", sa.String(length=32), nullable=True),
        sa.Column("evidence_url", sa.String(length=2048), nullable=True),
        sa.Column("evidence_reference", sa.String(length=2048), nullable=True),
        sa.Column("notes", sa.String(length=4096), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("performance_id", name=op.f("pk_content_performance_records")),
        sa.UniqueConstraint(
            "platform",
            "content_id",
            "period_start",
            "period_end",
            name=op.f("uq_content_performance_records_period"),
        ),
    )
    op.create_index(op.f("ix_content_performance_records_platform"), "content_performance_records", ["platform"])
    op.create_index(op.f("ix_content_performance_records_content_id"), "content_performance_records", ["content_id"])
    op.create_index(op.f("ix_content_performance_records_period_start"), "content_performance_records", ["period_start"])


def downgrade() -> None:
    op.drop_index(op.f("ix_content_performance_records_period_start"), table_name="content_performance_records")
    op.drop_index(op.f("ix_content_performance_records_content_id"), table_name="content_performance_records")
    op.drop_index(op.f("ix_content_performance_records_platform"), table_name="content_performance_records")
    op.drop_table("content_performance_records")
