"""Add created_by and updated_by to contact

Revision ID: add_created_by_updated_by_to_contact
Revises: d21817131c8a
Create Date: 2026-03-25 22:58:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_created_by_updated_by_to_contact'
down_revision = 'd21817131c8a'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('contacts', sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('contacts', sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))

def downgrade():
    op.drop_column('contacts', 'updated_by')
    op.drop_column('contacts', 'created_by')