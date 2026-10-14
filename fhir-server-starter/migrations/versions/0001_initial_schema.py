"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-10-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS organization_v2_pub_seq START 190000 INCREMENT 1")
    op.create_table(
        "organization_v2",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.BigInteger(),
            server_default=sa.text("nextval('organization_v2_pub_seq')"),
            nullable=False,
            unique=True,
        ),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("alias", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("identifier", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("type", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("telecom", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("address", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("contact", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("endpoint", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("partof_type", sa.String(), nullable=True),
        sa.Column("partof_id", sa.BigInteger(), nullable=True),
        sa.Column("partof_display", sa.String(), nullable=True),
        sa.Column("part_of", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_organization_v2_organization_id", "organization_v2", ["organization_id"], unique=True)
    op.create_index("ix_organization_v2_org_id", "organization_v2", ["org_id"])
    op.create_index("ix_organization_v2_name", "organization_v2", ["name"])
    op.create_index("ix_organization_v2_active", "organization_v2", ["active"])
    op.create_index("ix_organization_v2_partof_id", "organization_v2", ["partof_id"])

    # GIN Indexes
    op.create_index(
        "ix_organization_v2_identifier",
        "organization_v2",
        ["identifier"],
        postgresql_using="gin",
        postgresql_ops={"identifier": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_organization_v2_type",
        "organization_v2",
        ["type"],
        postgresql_using="gin",
        postgresql_ops={"type": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_organization_v2_telecom",
        "organization_v2",
        ["telecom"],
        postgresql_using="gin",
        postgresql_ops={"telecom": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_organization_v2_address",
        "organization_v2",
        ["address"],
        postgresql_using="gin",
        postgresql_ops={"address": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_organization_v2_contact",
        "organization_v2",
        ["contact"],
        postgresql_using="gin",
        postgresql_ops={"contact": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_organization_v2_endpoint",
        "organization_v2",
        ["endpoint"],
        postgresql_using="gin",
        postgresql_ops={"endpoint": "jsonb_path_ops"},
    )


def downgrade() -> None:
    op.drop_table("organization_v2")
    op.execute("DROP SEQUENCE IF EXISTS organization_v2_pub_seq")
