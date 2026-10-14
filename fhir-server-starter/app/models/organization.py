from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Sequence,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base

organization_v2_id_seq = Sequence(
    "organization_v2_pub_seq", start=190000, increment=1, metadata=Base.metadata
)
organization_id_seq = organization_v2_id_seq


class OrganizationV2Model(Base):
    """Organization resource model following a JSONB-separated design.

    Instead of flattening multi-value or complex FHIR datatypes into rigid
    0..1 scalar columns or dumping everything into a single monolithic
    `content`/`fhir_data` JSONB column (or creating numerous normalized child tables),
    this model stores repeating and complex FHIR datatypes as dedicated
    JSONB columns (`address`, `telecom`, `identifier`, `type`, `contact`,
    `endpoint`, `alias`).

    The monolithic `content`/`fhir_data` column is completely removed. High-frequency
    scalar search and identity fields (`name`, `active`, `org_id`,
    `organization_id`, `partof_id`) remain first-class columns for fast
    indexing, joins, and queries.
    """

    __tablename__ = "organization_v2"

    # Identity
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(
        BigInteger,
        organization_v2_id_seq,
        server_default=organization_v2_id_seq.next_value(),
        unique=True,
        index=True,
        nullable=False,
    )
    org_id = Column(String, nullable=False, index=True)

    # Core scalars / primary search fields
    name = Column(String, nullable=False, index=True)
    active = Column(Boolean, nullable=False, default=True, index=True)

    # Complex / repeating datatypes stored as dedicated JSONB arrays
    alias = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    identifier = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    type = Column("type", JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    telecom = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    address = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    contact = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    endpoint = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    # Reference(Organization) - part_of hierarchy
    partof_type = Column(String, nullable=True)
    partof_id = Column(BigInteger, nullable=True, index=True)
    partof_display = Column(String, nullable=True)
    part_of = Column(JSONB, nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=True)

    __table_args__ = (
        Index(
            "ix_organization_v2_identifier",
            "identifier",
            postgresql_using="gin",
            postgresql_ops={"identifier": "jsonb_path_ops"},
        ),
        Index(
            "ix_organization_v2_type",
            "type",
            postgresql_using="gin",
            postgresql_ops={"type": "jsonb_path_ops"},
        ),
        Index(
            "ix_organization_v2_telecom",
            "telecom",
            postgresql_using="gin",
            postgresql_ops={"telecom": "jsonb_path_ops"},
        ),
        Index(
            "ix_organization_v2_address",
            "address",
            postgresql_using="gin",
            postgresql_ops={"address": "jsonb_path_ops"},
        ),
        Index(
            "ix_organization_v2_contact",
            "contact",
            postgresql_using="gin",
            postgresql_ops={"contact": "jsonb_path_ops"},
        ),
        Index(
            "ix_organization_v2_endpoint",
            "endpoint",
            postgresql_using="gin",
            postgresql_ops={"endpoint": "jsonb_path_ops"},
        ),
    )


OrganizationModel = OrganizationV2Model
