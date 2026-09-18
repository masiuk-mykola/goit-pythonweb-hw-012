"""Add users.role and users.refresh_token

Revision ID: b7d2e4f1a9c3
Revises: a3f1c9d2b7e4
Create Date: 2026-09-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7d2e4f1a9c3'
down_revision: Union[str, Sequence[str], None] = 'a3f1c9d2b7e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

userrole = postgresql.ENUM('user', 'admin', name='userrole', create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    userrole.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'users',
        sa.Column('role', userrole, server_default='user', nullable=False),
    )
    op.add_column(
        'users', sa.Column('refresh_token', sa.String(length=512), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'refresh_token')
    op.drop_column('users', 'role')
    userrole.drop(op.get_bind(), checkfirst=True)
