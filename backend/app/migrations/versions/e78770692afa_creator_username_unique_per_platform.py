"""creator username unique per platform

Revision ID: e78770692afa
Revises: dae031bc730a
Create Date: 2026-08-21 12:07:30.165758

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision = "e78770692afa"
down_revision = "dae031bc730a"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("creator_username_key", "creator", type_="unique")
    op.create_unique_constraint(
        "uq_creator_platform_username", "creator", ["platform", "username"]
    )


def downgrade():
    op.drop_constraint("uq_creator_platform_username", "creator", type_="unique")
    op.create_unique_constraint(
        "creator_username_key", "creator", ["username"]
    )
