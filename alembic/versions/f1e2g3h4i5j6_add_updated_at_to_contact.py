"""Add updated_at to Contact"""
from alembic import op
import sqlalchemy as sa

revision = 'f1e2g3h4i5j6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add updated_at column to contacts table
    op.add_column('contacts', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True))


def downgrade():
    op.drop_column('contacts', 'updated_at')
