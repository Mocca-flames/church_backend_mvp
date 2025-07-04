"""Update contact model to use phone instead of phone_number"""
from alembic import op
import sqlalchemy as sa

revision = '12a6c2fbf7a0'
down_revision = '6924d1496162'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('contacts', 'phone_number', new_column_name='phone', existing_type=sa.String(length=20))
    op.drop_index('ix_contacts_phone_number', table_name='contacts')
    op.create_index(op.f('ix_contacts_phone'), 'contacts', ['phone'], unique=True)


def downgrade():
    op.alter_column('contacts', 'phone', new_column_name='phone_number', existing_type=sa.String(length=20))
    op.drop_index(op.f('ix_contacts_phone'), table_name='contacts')
    op.create_index('ix_contacts_phone_number', 'contacts', ['phone_number'], unique=True)
