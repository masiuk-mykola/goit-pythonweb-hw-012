"""Add users and contacts.user_id

Existing contacts have no owner, so they are removed before the non-null
user_id column is added.

Revision ID: a3f1c9d2b7e4
Revises: 0027183ec728
Create Date: 2026-09-15 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f1c9d2b7e4'
down_revision: Union[str, Sequence[str], None] = '0027183ec728'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('avatar', sa.String(length=255), nullable=True),
    sa.Column('confirmed', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.execute('DELETE FROM contacts')
    op.add_column('contacts', sa.Column('user_id', sa.Integer(), nullable=False))
    op.create_foreign_key(
        'contacts_user_id_fkey', 'contacts', 'users', ['user_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('contacts_user_id_fkey', 'contacts', type_='foreignkey')
    op.drop_column('contacts', 'user_id')
    op.drop_table('users')
