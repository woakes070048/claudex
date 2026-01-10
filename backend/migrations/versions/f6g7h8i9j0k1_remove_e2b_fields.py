"""remove e2b fields and sandbox_provider

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-01-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('user_settings', 'e2b_api_key')
    op.drop_column('user_settings', 'sandbox_provider')
    op.drop_column('chats', 'sandbox_provider')


def downgrade() -> None:
    op.add_column(
        'chats',
        sa.Column('sandbox_provider', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'user_settings',
        sa.Column('sandbox_provider', sa.String(length=20), nullable=False, server_default='docker')
    )
    op.add_column(
        'user_settings',
        sa.Column('e2b_api_key', sa.Text(), nullable=True)
    )
