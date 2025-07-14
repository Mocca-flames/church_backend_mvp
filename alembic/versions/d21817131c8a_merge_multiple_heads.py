"""Merge multiple heads"""
from alembic import op
import sqlalchemy as sa

revision = 'd21817131c8a'
down_revision = ('8aef6be8a835', 'bfa5bc1d9ac7', 'cfbc63195e49')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
