"""Make Contact name nullable in DB"""
from alembic import op
import sqlalchemy as sa

revision = '8db257f77c62'
down_revision = '239ca548b15f'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('contacts', 'name',
               existing_type=sa.VARCHAR(200),
               nullable=True,
               existing_nullable=False)

def downgrade():
    op.alter_column('contacts', 'name',
               existing_type=sa.VARCHAR(200),
               nullable=False,
               existing_nullable=True)
