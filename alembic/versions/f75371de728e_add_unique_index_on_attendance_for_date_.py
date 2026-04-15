"""Add unique index on attendance for date-based uniqueness"""

from alembic import op
import sqlalchemy as sa

revision = "f75371de728e"
down_revision = "420f19ad8cc0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_unique_attendance_date",
        "attendance",
        ["contact_id", "service_type", sa.text("date(service_date)")],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_unique_attendance_date", "attendance")
