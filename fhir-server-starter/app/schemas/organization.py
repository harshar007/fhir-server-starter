from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IdentifierSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system: str | None = None
    value: str | None = None
    use: str | None = None  # usual | official | temp | secondary | old


class CodeableConceptSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system: str | None = None
    code: str | None = None
    display: str | None = None
    text: str | None = None


class TelecomSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system: str | None = None  # phone | fax | email | pager | url | sms | other
    value: str | None = None
    use: str | None = None  # home | work | temp | old | mobile
    # rank: int | None = None
    # period: dict | None = None  # { "start": "2023-01-01", "end": "2023-12-31" }


class AddressSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use: str | None = None  # home | work | temp | old | billing
    line: list[str] = []
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class ContactSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: str | None = None
    name: str | None = None
    telecom: list[TelecomSchema] = []


class ReferenceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: str | None = None
    type: str | None = None
    display: str | None = None


class OrganizationCreateSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Acme Health Clinic",
                "active": True,
                "org_id": "org-test",
                "identifier": [{"system": "urn:example:tax-id", "value": "12-3456789", "use": "official"}],
                "type": [{"system": "http://terminology.hl7.org/CodeSystem/organization-type", "code": "prov", "display": "Healthcare Provider"}],
                "alias": ["Acme Clinic"],
                "telecom": [{"system": "phone", "value": "+1-555-0100", "use": "work"}],
                "address": [{"use": "work", "line": ["123 Main St"], "city": "Springfield", "state": "IL", "postal_code": "62701", "country": "US"}],
                "contact": [],
                "endpoint": [],
                "part_of": None,
            }
        },
    )

    name: str
    active: bool = True
    org_id: str | None = None  # Populated from JWT actor if omitted
    identifier: list[IdentifierSchema] = []
    type: list[CodeableConceptSchema] = []
    alias: list[str] = []
    telecom: list[TelecomSchema] = []
    address: list[AddressSchema] = []
    contact: list[ContactSchema] = []
    endpoint: list[ReferenceSchema] = []
    part_of: int | ReferenceSchema | None = None  # organization_id or Reference of the parent


class OrganizationPatchSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    active: bool | None = None
    org_id: str | None = None
    identifier: list[IdentifierSchema] | None = None
    type: list[CodeableConceptSchema] | None = None
    alias: list[str] | None = None
    telecom: list[TelecomSchema] | None = None
    address: list[AddressSchema] | None = None
    contact: list[ContactSchema] | None = None
    endpoint: list[ReferenceSchema] | None = None
    part_of: int | ReferenceSchema | None = None


class PlainOrganizationResponse(BaseModel):
    id: int
    org_id: str
    name: str
    active: bool
    identifier: list[IdentifierSchema] = []
    type: list[CodeableConceptSchema] = []
    alias: list[str] = []
    telecom: list[TelecomSchema] = []
    address: list[AddressSchema] = []
    contact: list[ContactSchema] = []
    endpoint: list[ReferenceSchema] = []
    part_of: int | None = None
    partof_id: int | None = None
    partof_display: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FHIROrganizationSchema(BaseModel):
    """Documents the FHIR R4 camelCase shape for OpenAPI/MCP tooling — the
    actual response is hand-built by app/fhir/mappers/organization/fhir.py;
    this class exists only so /docs shows a real-looking shape."""

    resourceType: str = "Organization"
    id: str
    active: bool | None = None
    name: str | None = None
    alias: list[str] | None = None
    identifier: list[dict] | None = None
    type: list[dict] | None = None
    telecom: list[dict] | None = None
    address: list[dict] | None = None
    contact: list[dict] | None = None
    endpoint: list[dict] | None = None
    partOf: dict | None = None


class PaginatedOrganizationResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: list[PlainOrganizationResponse]


class FHIROrganizationBundle(BaseModel):
    resourceType: str = "Bundle"
    type: str = "searchset"
    total: int
    entry: list[dict]
