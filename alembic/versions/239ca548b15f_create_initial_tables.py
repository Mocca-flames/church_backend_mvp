"""Create initial tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

revision = '239ca548b15f'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='active'),
        sa.Column('opt_out_sms', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('opt_out_whatsapp', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('metadata_', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contacts_id'), 'contacts', ['id'], unique=False)
    op.create_index(op.f('ix_contacts_phone'), 'contacts', ['phone'], unique=True)

    op.create_table(
        'communications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('recipient_group', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='draft'),
        sa.Column('sent_count', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('failed_count', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('metadata_', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_communications_id'), 'communications', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_communications_id'), table_name='communications')
    op.drop_table('communications')
    op.drop_index(op.f('ix_contacts_phone'), table_name='contacts')
    op.drop_index(op.f('ix_contacts_id'), table_name='contacts')
    op.drop_table('contacts')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
