"""Initial users, expenses, and conversation_states tables.

Revision ID: 20260827_0001
Revises:
Create Date: 2026-08-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("whatsapp_number", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=8), server_default="INR", nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Kolkata", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("whatsapp_number", name="uq_users_whatsapp_number"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_users_whatsapp_number", "users", ["whatsapp_number"], unique=False)

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default="INR", nullable=False),
        sa.Column("merchant", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=32), server_default="Other", nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("client", sa.String(length=255), nullable=True),
        sa.Column("project", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("source", sa.String(length=32), server_default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_expenses_user_id", "expenses", ["user_id"], unique=False)
    op.create_index("ix_expenses_expense_date", "expenses", ["expense_date"], unique=False)
    op.create_index("ix_expenses_category", "expenses", ["category"], unique=False)

    op.create_table(
        "conversation_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=64), server_default="IDLE", nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_conversation_states_user_id"),
        mysql_engine="InnoDB",
    )


def downgrade() -> None:
    op.drop_table("conversation_states")
    op.drop_index("ix_expenses_category", table_name="expenses")
    op.drop_index("ix_expenses_expense_date", table_name="expenses")
    op.drop_index("ix_expenses_user_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_users_whatsapp_number", table_name="users")
    op.drop_table("users")
