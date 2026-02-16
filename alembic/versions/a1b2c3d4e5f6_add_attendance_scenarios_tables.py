"""Add attendance, scenarios, and scenario_tasks tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

revision = 'a1b2c3d4e5f6'
down_revision = 'd21817131c8a'
branch_labels = None
depends_on = None


def upgrade():
    # Create attendance table
    op.create_table(
        'attendance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('service_type', sa.String(length=50), nullable=False),
        sa.Column('service_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_by', sa.Integer(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attendance_id'), 'attendance', ['id'], unique=False)
    op.create_index(op.f('ix_attendance_contact_id'), 'attendance', ['contact_id'], unique=False)
    op.create_index(op.f('ix_attendance_service_date'), 'attendance', ['service_date'], unique=False)

    # Create scenarios table
    op.create_table(
        'scenarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('filter_tags', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='active'),
        sa.Column('is_deleted', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scenarios_id'), 'scenarios', ['id'], unique=False)
    op.create_index(op.f('ix_scenarios_status'), 'scenarios', ['status'], unique=False)

    # Create scenario_tasks table
    op.create_table(
        'scenario_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scenario_id', sa.Integer(), nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('completed_by', sa.Integer(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.id']),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['completed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scenario_tasks_id'), 'scenario_tasks', ['id'], unique=False)
    op.create_index(op.f('ix_scenario_tasks_scenario_id'), 'scenario_tasks', ['scenario_id'], unique=False)


def downgrade():
    op.drop_table('scenario_tasks')
    op.drop_table('scenarios')
    op.drop_table('attendance')
