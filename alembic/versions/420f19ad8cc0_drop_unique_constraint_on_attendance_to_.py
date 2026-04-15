"""Drop unique constraint on attendance to adjust for date-based uniqueness"""
from alembic import op
import sqlalchemy as sa

revision = '420f19ad8cc0'
down_revision = '7cdabf9cf92d'
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
