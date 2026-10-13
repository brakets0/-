"""add user face registration fields

Revision ID: 0002_user_face_token
Revises: 0001_initial
Create Date: 2026-10-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_user_face_token"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("face_token", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users", sa.Column("face_registered_at", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "face_registered_at")
    op.drop_column("users", "face_token")
