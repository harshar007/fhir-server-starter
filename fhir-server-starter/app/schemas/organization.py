from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CodingSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system: str | None = None
    version: str | None = None
    code: str | None = None
    display: str | None = None
    userSelected: bool | None = None


class CodeableConceptSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system: str | None = None  # Shorthand for convenience
    code: str | None = None
    display: str | None = None
    coding: list[CodingSchema] = []
    text: str | None = None


class PeriodSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: str | None = None
    end: str | None = None


class ReferenceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: str | None = None
    type: str | None = None
    identifier: dict | None = None
    display: str | None = None


class IdentifierSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use: str | None = None  # usual | official | temp | secondary | old
    type: CodeableConceptSchema | dict | None = None
    system: str | None = None
    value: str | None = None
    period: PeriodSchema | dict | None = None
    assigner: ReferenceSchema | dict | None = None


class TelecomSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system: str | None = None  # phone | fax | email | pager | url | sms | other
    value: str | None = None
    use: str | None = None  # home | work | temp | old | mobile
    rank: int | None = None
    period: PeriodSchema | dict | None = None


class AddressSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use: str | None = None  # home | work | temp | old | billing
    type: str | None = None  # postal | physical | both
    text: str | None = None
    line: list[str] = []
    city: str | None = None
    district: str | None = None
    state: str | None = None
    postal_code: str | None = None
    postalCode: str | None = None  # FHIR camelCase alias
    country: str | None = None
    period: PeriodSchema | dict | None = None

    def model_dump(self, *args, **kwargs):
        d = super().model_dump(*args, **kwargs)
        if d.get("postalCode") and not d.get("postal_code"):
            d["postal_code"] = d["postalCode"]
        return d


class HumanNameSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use: str | None = None  # usual | official | temp | nickname | anonymous | old | maiden
    text: str | None = None
    family: str | None = None
    given: list[str] = []
    prefix: list[str] = []
    suffix: list[str] = []
    period: PeriodSchema | dict | None = None


class ContactSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: CodeableConceptSchema | dict | str | None = None
    name: HumanNameSchema | dict | str | None = None
    telecom: list[TelecomSchema] = []
    address: AddressSchema | dict | None = None


class MetaSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    versionId: str | None = None
    lastUpdated: str | None = None
    source: str | None = None
    profile: list[str] = []
    security: list[CodingSchema] = []
    tag: list[CodingSchema] = []


class NarrativeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str | None = None  # generated | extensions | additional | empty
    div: str | None = None


class OrganizationCreateSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "resourceType": "Organization",
                "name": "Acme Health System",
                "active": True,
                "org_id": "org-test",
                "alias": ["Acme Health", "AHS"],
                "identifier": [
                    {
                        "use": "official",
                        "system": "http://hl7.org/fhir/sid/us-npi",
                        "value": "1234567890",
                    }
                ],
                "type": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/organization-type",
                                "code": "prov",
                                "display": "Healthcare Provider",
                            }
                        ],
                        "text": "Healthcare Provider",
                    }
                ],
                "telecom": [
                    {
                        "system": "phone",
                        "value": "+1-555-0100",
                        "use": "work",
                        "rank": 1,
                    }
                ],
                "address": [
                    {
                        "use": "work",
                        "type": "both",
                        "text": "123 Main St, Springfield, IL 62701",
                        "line": ["123 Main St"],
                        "city": "Springfield",
                        "district": "Sangamon",
                        "state": "IL",
                        "postal_code": "62701",
                        "country": "USA",
                    }
                ],
                "part_of": None,
                "contact": [
                    {
                        "purpose": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/contactentity-type",
                                    "code": "ADMIN",
                                    "display": "Administrative",
                                }
                            ]
                        },
                        "name": {
                            "use": "official",
                            "text": "Dr. Sarah Connor",
                            "family": "Connor",
                            "given": ["Sarah"],
                            "prefix": ["Dr."],
                        },
                        "telecom": [
                            {
                                "system": "email",
                                "value": "sconnor@acmehealth.org",
                                "use": "work",
                            }
                        ],
                        "address": {
                            "line": ["123 Main St, Suite 400"],
                            "city": "Springfield",
                            "state": "IL",
                            "postal_code": "62701",
                        },
                    }
                ],
                "endpoint": [
                    {
                        "reference": "Endpoint/ep-1",
                        "display": "Acme FHIR Service",
                    }
                ],
            }
        },
    )

    resourceType: str | None = "Organization"
    name: str
    active: bool = True
    org_id: str | None = None  # Populated from JWT actor if omitted
    alias: list[str] = []
    identifier: list[IdentifierSchema] = []
    type: list[CodeableConceptSchema] = []
    telecom: list[TelecomSchema] = []
    address: list[AddressSchema] = []
    contact: list[ContactSchema] = []
    endpoint: list[ReferenceSchema] = []
    part_of: int | ReferenceSchema | None = None
    meta: MetaSchema | dict | None = None
    implicitRules: str | None = None
    language: str | None = None
    text: NarrativeSchema | dict | None = None
    contained: list[dict] = []
    extension: list[dict] = []
    modifierExtension: list[dict] = []


class OrganizationPatchSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resourceType: str | None = "Organization"
    id: str | int | None = None
    name: str | None = None
    active: bool | None = None
    org_id: str | None = None
    alias: list[str] | None = None
    identifier: list[IdentifierSchema] | None = None
    type: list[CodeableConceptSchema] | None = None
    telecom: list[TelecomSchema] | None = None
    address: list[AddressSchema] | None = None
    contact: list[ContactSchema] | None = None
    endpoint: list[ReferenceSchema] | None = None
    part_of: int | ReferenceSchema | None = None
    meta: MetaSchema | dict | None = None
    implicitRules: str | None = None
    language: str | None = None
    text: NarrativeSchema | dict | None = None
    contained: list[dict] | None = None
    extension: list[dict] | None = None
    modifierExtension: list[dict] | None = None


class PlainOrganizationResponse(BaseModel):
    id: int
    org_id: str
    name: str
    active: bool
    alias: list[str] = []
    identifier: list[dict] = []
    type: list[dict] = []
    telecom: list[dict] = []
    address: list[dict] = []
    contact: list[dict] = []
    endpoint: list[dict] = []
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
    this class exists only so /docs shows the complete real FHIR R4 shape."""

    resourceType: str = "Organization"
    id: str
    meta: dict | None = None
    implicitRules: str | None = None
    language: str | None = None
    text: dict | None = None
    contained: list[dict] | None = None
    extension: list[dict] | None = None
    modifierExtension: list[dict] | None = None
    identifier: list[dict] | None = None
    active: bool | None = None
    type: list[dict] | None = None
    name: str | None = None
    alias: list[str] | None = None
    telecom: list[dict] | None = None
    address: list[dict] | None = None
    partOf: dict | None = None
    contact: list[dict] | None = None
    endpoint: list[dict] | None = None


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


class OrganizationSearchParams(BaseModel):
    model_config = ConfigDict(extra="allow")

    _id: str | None = None
    active: str | None = None
    name: str | None = None
    phonetic: str | None = None
    identifier: str | None = None
    type: str | None = None
    address: str | None = None
    address_city: str | None = None
    address_country: str | None = None
    address_postalcode: str | None = None
    address_state: str | None = None
    address_use: str | None = None
    endpoint: str | None = None
    partof: str | None = None

    # Modifiers
    name_exact: bool = False
    name_contains: bool = False

    # :missing modifier flags
    _id_missing: bool | None = None
    active_missing: bool | None = None
    name_missing: bool | None = None
    phonetic_missing: bool | None = None
    identifier_missing: bool | None = None
    type_missing: bool | None = None
    address_missing: bool | None = None
    address_city_missing: bool | None = None
    address_country_missing: bool | None = None
    address_postalcode_missing: bool | None = None
    address_state_missing: bool | None = None
    address_use_missing: bool | None = None
    endpoint_missing: bool | None = None
    partof_missing: bool | None = None

    # Pagination & sorting
    sort: str | None = None
    limit: int = 50
    offset: int = 0


class OrganizationSearchBody(BaseModel):
    """FHIR R4 / Medplum Organization search parameters for POST /_search body.

    Reference:
    https://www.medplum.com/docs/api/fhir/resources/organization?section=schema#search-parameters
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "name": "St. Jude",
                "active": "true",
                "address-city": "Memphis",
                "_sort": "name",
                "_count": 10,
                "_offset": 0,
            }
        },
    )

    id: str | None = Field(None, alias="_id", description="Logical id of this artifact (Resource.id)")
    active: str | None = Field(None, description="Is the Organization record active (Organization.active: true | false)")
    name: str | None = Field(None, description="A portion of the organization's name or alias (Organization.name | Organization.alias)")
    phonetic: str | None = Field(None, description="A portion of the organization's name using soundex/phonetic matching algorithm (Organization.name)")
    identifier: str | None = Field(None, description="Any identifier for the organization (Organization.identifier). Format: [system]|[value] or [value]")
    type: str | None = Field(None, description="A code for the type of organization (Organization.type). Format: [system]|[code] or [code]")
    address: str | None = Field(None, description="A server defined search that matches any string field in Address (line, city, district, state, country, postalCode, text)")
    address_city: str | None = Field(None, alias="address-city", description="A city specified in an address (Organization.address.city)")
    address_country: str | None = Field(None, alias="address-country", description="A country specified in an address (Organization.address.country)")
    address_postalcode: str | None = Field(None, alias="address-postalcode", description="A postal code specified in an address (Organization.address.postalCode)")
    address_state: str | None = Field(None, alias="address-state", description="A state specified in an address (Organization.address.state)")
    address_use: str | None = Field(None, alias="address-use", description="A use code specified in an address (Organization.address.use: home | work | temp | old | billing)")
    endpoint: str | None = Field(None, description="Technical endpoints providing access to services operated for the organization (Organization.endpoint)")
    partof: str | None = Field(None, alias="partof", description="An organization of which this organization forms a part (Organization.partOf)")

    sort: str | None = Field(None, alias="_sort", description="Sort order (e.g. name, -name, _id, -id, active, -active)")
    count: int | None = Field(None, alias="_count", ge=1, le=200, description="Page size limit (FHIR / Medplum standard _count)")
    offset: int | None = Field(None, alias="_offset", ge=0, description="Page offset (FHIR / Medplum standard _offset)")


def parse_organization_search_params(raw_params: dict[str, str]) -> OrganizationSearchParams:
    """Parses raw query parameters or form fields into OrganizationSearchParams,
    handling FHIR conventions such as hyphenated parameters (address-city),
    standard FHIR aliases (_count, _offset, _sort), and modifiers (:missing, :exact, :contains).
    """
    data: dict = {}

    for key, value in raw_params.items():
        if value is None:
            continue
        v_str = str(value).strip()

        # Handle :missing modifier
        if key.endswith(":missing"):
            param_base = key[:-8].lower().replace("-", "_")
            if param_base == "part_of":
                param_base = "partof"
            is_missing = v_str.lower() in ("true", "1")
            data[f"{param_base}_missing"] = is_missing
            continue

        # Handle :exact modifier
        if key == "name:exact":
            data["name"] = v_str
            data["name_exact"] = True
            continue

        # Handle :contains modifier
        if key == "name:contains":
            data["name"] = v_str
            data["name_contains"] = True
            continue

        # Normalize key
        k_lower = key.lower()

        if k_lower in ("_id", "id"):
            data["_id"] = v_str
        elif k_lower == "active":
            data["active"] = v_str
        elif k_lower == "name":
            data["name"] = v_str
        elif k_lower == "phonetic":
            data["phonetic"] = v_str
        elif k_lower == "identifier":
            data["identifier"] = v_str
        elif k_lower == "type":
            data["type"] = v_str
        elif k_lower == "address":
            data["address"] = v_str
        elif k_lower in ("address-city", "address_city"):
            data["address_city"] = v_str
        elif k_lower in ("address-country", "address_country"):
            data["address_country"] = v_str
        elif k_lower in ("address-postalcode", "address_postalcode", "address-postal-code"):
            data["address_postalcode"] = v_str
        elif k_lower in ("address-state", "address_state"):
            data["address_state"] = v_str
        elif k_lower in ("address-use", "address_use"):
            data["address_use"] = v_str
        elif k_lower == "endpoint":
            data["endpoint"] = v_str
        elif k_lower in ("partof", "part_of"):
            data["partof"] = v_str
        elif k_lower in ("_count", "limit"):
            try:
                data["limit"] = int(v_str)
            except ValueError:
                pass
        elif k_lower in ("_offset", "offset"):
            try:
                data["offset"] = int(v_str)
            except ValueError:
                pass
        elif k_lower in ("_sort", "sort"):
            data["sort"] = v_str

    return OrganizationSearchParams(**data)

