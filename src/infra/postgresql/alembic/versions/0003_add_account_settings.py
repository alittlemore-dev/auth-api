from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth__user_model",
        sa.Column(
            "settings",
            postgresql.JSONB(),
            server_default=sa.literal("{}"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("auth__user_model", "settings")
