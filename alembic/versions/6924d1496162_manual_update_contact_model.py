"""Manual update contact model

Revision ID: 6924d1496162
Revises: 
Create Date: 2025-07-03 20:14:34.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6924d1496162'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('contacts', sa.Column('name', sa.String(length=200), nullable=False))
    op.add_column('contacts', sa.Column('phone_number', sa.String(length=20), nullable=False))
    op.drop_index('ix_contacts_phone', table_name='contacts')
    op.create_index(op.f('ix_contacts_phone_number'), 'contacts', ['phone_number'], unique=True)
    op.drop_column('contacts', 'full_name')
    op.drop_column('contacts', 'phone')


def downgrade():
    op.add_column('contacts', sa.Column('phone', sa.VARCHAR(length=20), autoincrement=False, nullable=False))
    op.add_column('contacts', sa.Column('full_name', sa.VARCHAR(length=200), autoincrement=False, nullable=False))
    op.drop_index(op.f('ix_contacts_phone_number'), table_name='contacts')
    op.create_index('ix_contacts_phone', 'contacts', ['phone'], unique=True)
    op.drop_column('contacts', 'phone_number')
    op.drop_column('contacts', 'name')
