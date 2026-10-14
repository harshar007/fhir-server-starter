from fastapi import APIRouter, Body, Depends, Query, Request, status

from app.auth.models import AuthUser
from app.auth.rbac import require_permission
from app.core.content_negotiation import format_paginated_response, format_response
from app.core.logging import get_logger
from app.core.schema_utils import inline_schema
from app.errors.domain import NotFoundError
from app.di.dependencies.organization import get_organization_service
from app.schemas.organization import (
    FHIROrganizationBundle,
    FHIROrganizationSchema,
    OrganizationCreateSchema,
    OrganizationPatchSchema,
    OrganizationSearchBody,
    OrganizationSearchParams,
    PaginatedOrganizationResponse,
    PlainOrganizationResponse,
    parse_organization_search_params,
)
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])
logger = get_logger(__name__)

_CONTENT_NEG = (
    "Set `Accept: application/fhir+json` for the full FHIR R4 representation; "
    "omit or use `Accept: application/json` for the simplified plain-JSON form."
)

_SINGLE_200 = {
    200: {
        "content": {
            "application/json": {"schema": inline_schema(PlainOrganizationResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FHIROrganizationSchema.model_json_schema())},
        }
    }
}
_SINGLE_201 = {201: _SINGLE_200[200]}
_LIST_200 = {
    200: {
        "content": {
            "application/json": {"schema": inline_schema(PaginatedOrganizationResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FHIROrganizationBundle.model_json_schema())},
        }
    }
}
_ERR_NOT_FOUND = {404: {"description": "Organization not found"}}
_ERR_VALIDATION = {422: {"description": "Failed FHIR base R4 validation — real OperationOutcome body"}}


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_organization",
    summary="Create a new Organization resource",
    description="Validates the resulting FHIR R4 resource (app/fhir/validation/base_r4.py) before "
    "persisting — an invalid payload never reaches the database. created_by comes from the verified "
    "JWT's `sub` claim, not the request body. " + _CONTENT_NEG,
    responses={**_SINGLE_201, **_ERR_VALIDATION},
)
async def create_organization(
    payload: OrganizationCreateSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("organization", "create")),
    service: OrganizationService = Depends(get_organization_service),
):
    logger.info("Create a new Organization resource", extra={"event": "route.create_organization"})
    org = await service.create_organization(payload, created_by=actor.sub, org_id=actor.org_id)
    return format_response(service.to_fhir(org), service.to_plain(org), request, status_code=status.HTTP_201_CREATED)


_MEDPLUM_SEARCH_DESCRIPTION = (
    "Search Organization resources per the [Medplum FHIR R4 Organization Search Specification]"
    "(https://www.medplum.com/docs/api/fhir/resources/organization?section=schema#search-parameters).\n\n"
    "### Supported Medplum / FHIR Search Parameters\n\n"
    "| Search Parameter | Type | Expression | Description |\n"
    "| :--- | :--- | :--- | :--- |\n"
    "| `_id` | `token` | `Resource.id` | Logical id of this artifact (Resource.id) |\n"
    "| `active` | `token` | `Organization.active` | Is the Organization record active (`true` \\| `false`) |\n"
    "| `address` | `string` | `Organization.address` | Matches any string field in Address (line, city, district, state, country, postalCode, text) |\n"
    "| `address-city` | `string` | `Organization.address.city` | A city specified in an address |\n"
    "| `address-country` | `string` | `Organization.address.country` | A country specified in an address |\n"
    "| `address-postalcode` | `string` | `Organization.address.postalCode` | A postal code specified in an address |\n"
    "| `address-state` | `string` | `Organization.address.state` | A state specified in an address |\n"
    "| `address-use` | `token` | `Organization.address.use` | A use code specified in an address (`home` \\| `work` \\| `temp` \\| `old` \\| `billing`) |\n"
    "| `endpoint` | `reference` | `Organization.endpoint` | Technical endpoints providing access to services operated for the organization |\n"
    "| `identifier` | `token` | `Organization.identifier` | Any identifier for the organization (`[system]\\|[value]` or `[value]`) |\n"
    "| `name` | `string` | `Organization.name \\| Organization.alias` | A portion of the organization's name or alias |\n"
    "| `partof` | `reference` | `Organization.partOf` | An organization of which this organization forms a part (`Organization/[id]`) |\n"
    "| `phonetic` | `string` | `Organization.name` | Soundex/phonetic matching on organization name |\n"
    "| `type` | `token` | `Organization.type` | A code for the type of organization (`[system]\\|[code]` or `[code]`) |\n\n"
    "### Common Search Parameters & Modifiers\n\n"
    "- `_sort`: Sort field (`name`, `-name`, `_id`, `-id`, `active`, `-active`)\n"
    "- `_count` / `_offset`: FHIR & Medplum pagination\n"
    "- `:exact`: Case-sensitive exact matching (e.g. `name:exact=Acme Health`)\n"
    "- `:contains`: Substring matching (e.g. `name:contains=Clinic`)\n"
    "- `:missing`: Check whether field is missing or present (`true` or `false`, e.g. `partof:missing=true`)\n\n"
)


class OrganizationQueryParams:
    """Declares all 13 Medplum Organization search parameters + common parameters
    so they render directly with interactive input fields in Swagger / OpenAPI UI (/docs).
    """

    def __init__(
        self,
        _id: str | None = Query(None, description="Logical id of this artifact (Resource.id / organization_id)", openapi_examples={"example1": {"summary": "Resource ID", "value": "190000"}}),
        active: str | None = Query(None, description="Is the Organization record active (Organization.active: true | false)", openapi_examples={"active": {"summary": "Active", "value": "true"}, "inactive": {"summary": "Inactive", "value": "false"}}),
        name: str | None = Query(None, description="A portion of the organization's name or alias (Organization.name | Organization.alias)", openapi_examples={"name": {"summary": "Name or Alias", "value": "St. Jude"}}),
        phonetic: str | None = Query(None, description="A portion of the organization's name using phonetic matching (Organization.name)"),
        identifier: str | None = Query(None, description="Any identifier for the organization (Organization.identifier). Format: [system]|[value] or [value]", openapi_examples={"npi": {"summary": "NPI", "value": "http://hl7.org/fhir/sid/us-npi|9876543210"}}),
        type: str | None = Query(None, description="A code for the type of organization (Organization.type). Format: [system]|[code] or [code]", openapi_examples={"prov": {"summary": "Healthcare Provider", "value": "http://terminology.hl7.org/CodeSystem/organization-type|prov"}}),
        address: str | None = Query(None, description="Matches any string field in Address (line, city, district, state, country, postalCode, text)"),
        address_city: str | None = Query(None, alias="address-city", description="A city specified in an address (Organization.address.city)", openapi_examples={"city": {"summary": "City", "value": "Memphis"}}),
        address_country: str | None = Query(None, alias="address-country", description="A country specified in an address (Organization.address.country)", openapi_examples={"country": {"summary": "Country", "value": "USA"}}),
        address_postalcode: str | None = Query(None, alias="address-postalcode", description="A postal code specified in an address (Organization.address.postalCode)", openapi_examples={"zip": {"summary": "Postal Code", "value": "38105"}}),
        address_state: str | None = Query(None, alias="address-state", description="A state specified in an address (Organization.address.state)", openapi_examples={"state": {"summary": "State", "value": "TN"}}),
        address_use: str | None = Query(None, alias="address-use", description="A use code specified in an address (Organization.address.use: home | work | temp | old | billing)", openapi_examples={"work": {"summary": "Work", "value": "work"}}),
        endpoint: str | None = Query(None, description="Technical endpoints providing access to services operated for the organization (Organization.endpoint)", openapi_examples={"endpoint": {"summary": "Endpoint Reference", "value": "Endpoint/ep-stjude-1"}}),
        partof: str | None = Query(None, alias="partof", description="An organization of which this organization forms a part (Organization.partOf)", openapi_examples={"partof": {"summary": "Parent Org", "value": "Organization/190001"}}),
        sort: str | None = Query(None, alias="_sort", description="Sort field (e.g. name, -name, _id, -id, active, -active)", openapi_examples={"sort_name": {"summary": "Sort by Name", "value": "name"}}),
        count: int | None = Query(None, alias="_count", ge=1, le=200, description="Page size limit (FHIR / Medplum standard _count)", openapi_examples={"count": {"summary": "Page Size", "value": 10}}),
        offset_param: int | None = Query(None, alias="_offset", ge=0, description="Page offset (FHIR / Medplum standard _offset)", openapi_examples={"offset": {"summary": "Page Offset", "value": 0}}),
        limit: int | None = Query(None, ge=1, le=200, description="Page limit (default 50)"),
        offset: int | None = Query(None, ge=0, description="Page offset (default 0)"),
    ):
        self._id = _id
        self.active = active
        self.name = name
        self.phonetic = phonetic
        self.identifier = identifier
        self.type = type
        self.address = address
        self.address_city = address_city
        self.address_country = address_country
        self.address_postalcode = address_postalcode
        self.address_state = address_state
        self.address_use = address_use
        self.endpoint = endpoint
        self.partof = partof
        self.sort = sort
        self.count = count
        self.offset_param = offset_param
        self.limit = limit
        self.offset = offset


def _resolve_search_params(request: Request, query: OrganizationQueryParams) -> tuple[OrganizationSearchParams, int, int]:
    # Parse all raw query params to capture FHIR modifiers (:missing, :exact, :contains, etc.)
    search_params = parse_organization_search_params(dict(request.query_params))

    # Fallback to declared FastAPI query parameter values if not captured via raw params
    if search_params._id is None and query._id is not None:
        search_params._id = query._id
    if search_params.active is None and query.active is not None:
        search_params.active = query.active
    if search_params.name is None and query.name is not None:
        search_params.name = query.name
    if search_params.phonetic is None and query.phonetic is not None:
        search_params.phonetic = query.phonetic
    if search_params.identifier is None and query.identifier is not None:
        search_params.identifier = query.identifier
    if search_params.type is None and query.type is not None:
        search_params.type = query.type
    if search_params.address is None and query.address is not None:
        search_params.address = query.address
    if search_params.address_city is None and query.address_city is not None:
        search_params.address_city = query.address_city
    if search_params.address_country is None and query.address_country is not None:
        search_params.address_country = query.address_country
    if search_params.address_postalcode is None and query.address_postalcode is not None:
        search_params.address_postalcode = query.address_postalcode
    if search_params.address_state is None and query.address_state is not None:
        search_params.address_state = query.address_state
    if search_params.address_use is None and query.address_use is not None:
        search_params.address_use = query.address_use
    if search_params.endpoint is None and query.endpoint is not None:
        search_params.endpoint = query.endpoint
    if search_params.partof is None and query.partof is not None:
        search_params.partof = query.partof
    if search_params.sort is None and query.sort is not None:
        search_params.sort = query.sort

    effective_limit = query.count if query.count is not None else (query.limit if query.limit is not None else (search_params.limit if "limit" in request.query_params or "_count" in request.query_params else 50))
    effective_offset = query.offset_param if query.offset_param is not None else (query.offset if query.offset is not None else (search_params.offset if "offset" in request.query_params or "_offset" in request.query_params else 0))
    search_params.limit = effective_limit
    search_params.offset = effective_offset
    return search_params, effective_limit, effective_offset


@router.get(
    "",
    include_in_schema=False,
    responses=_LIST_200,
)
@router.get(
    "/",
    operation_id="list_organizations",
    summary="Search Organization resources (Medplum / FHIR R4 standard)",
    description=_MEDPLUM_SEARCH_DESCRIPTION + _CONTENT_NEG,
    responses=_LIST_200,
)
async def list_organizations(
    request: Request,
    query: OrganizationQueryParams = Depends(),
    actor: AuthUser = Depends(require_permission("organization", "read")),
    service: OrganizationService = Depends(get_organization_service),
):
    search_params, effective_limit, effective_offset = _resolve_search_params(request, query)
    orgs, total = await service.list_organizations(
        params=search_params,
        limit=effective_limit,
        offset=effective_offset,
    )
    return format_paginated_response(
        [service.to_fhir(o) for o in orgs],
        [service.to_plain(o) for o in orgs],
        total,
        effective_limit,
        effective_offset,
        request,
    )


@router.get(
    "/_search",
    operation_id="search_organizations_get",
    summary="Search Organization resources (FHIR / Medplum GET _search)",
    description=_MEDPLUM_SEARCH_DESCRIPTION + _CONTENT_NEG,
    responses=_LIST_200,
)
async def search_organizations_get(
    request: Request,
    query: OrganizationQueryParams = Depends(),
    actor: AuthUser = Depends(require_permission("organization", "read")),
    service: OrganizationService = Depends(get_organization_service),
):
    search_params, effective_limit, effective_offset = _resolve_search_params(request, query)
    orgs, total = await service.list_organizations(
        params=search_params,
        limit=effective_limit,
        offset=effective_offset,
    )
    return format_paginated_response(
        [service.to_fhir(o) for o in orgs],
        [service.to_plain(o) for o in orgs],
        total,
        effective_limit,
        effective_offset,
        request,
    )


@router.post(
    "/_search",
    operation_id="search_organizations_post",
    summary="Search Organization resources (FHIR / Medplum POST _search)",
    description="Standard FHIR R4 POST search accepting search parameters in the request body "
    "(application/json or application/x-www-form-urlencoded) or URL query parameters per Medplum standard.\n\n"
    + _MEDPLUM_SEARCH_DESCRIPTION
    + _CONTENT_NEG,
    responses=_LIST_200,
    openapi_extra={
        "requestBody": {
            "required": False,
            "description": "FHIR / Medplum Organization search parameters (JSON or form-urlencoded)",
            "content": {
                "application/json": {"schema": inline_schema(OrganizationSearchBody.model_json_schema())},
                "application/x-www-form-urlencoded": {"schema": inline_schema(OrganizationSearchBody.model_json_schema())},
            },
        }
    },
)
async def search_organizations_post(
    request: Request,
    query: OrganizationQueryParams = Depends(),
    actor: AuthUser = Depends(require_permission("organization", "read")),
    service: OrganizationService = Depends(get_organization_service),
):
    raw_dict: dict[str, str] = {}
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        raw_dict.update({k: str(v) for k, v in form.items()})
    elif "application/json" in content_type:
        try:
            raw_json = await request.json()
            if isinstance(raw_json, dict):
                raw_dict.update({k: str(v) for k, v in raw_json.items() if v is not None})
        except Exception:
            pass

    # URL query parameters take precedence or merge
    raw_dict.update(dict(request.query_params))

    search_params = parse_organization_search_params(raw_dict)

    # Merge query params from dependency
    if search_params._id is None and query._id is not None:
        search_params._id = query._id
    if search_params.active is None and query.active is not None:
        search_params.active = query.active
    if search_params.name is None and query.name is not None:
        search_params.name = query.name
    if search_params.phonetic is None and query.phonetic is not None:
        search_params.phonetic = query.phonetic
    if search_params.identifier is None and query.identifier is not None:
        search_params.identifier = query.identifier
    if search_params.type is None and query.type is not None:
        search_params.type = query.type
    if search_params.address is None and query.address is not None:
        search_params.address = query.address
    if search_params.address_city is None and query.address_city is not None:
        search_params.address_city = query.address_city
    if search_params.address_country is None and query.address_country is not None:
        search_params.address_country = query.address_country
    if search_params.address_postalcode is None and query.address_postalcode is not None:
        search_params.address_postalcode = query.address_postalcode
    if search_params.address_state is None and query.address_state is not None:
        search_params.address_state = query.address_state
    if search_params.address_use is None and query.address_use is not None:
        search_params.address_use = query.address_use
    if search_params.endpoint is None and query.endpoint is not None:
        search_params.endpoint = query.endpoint
    if search_params.partof is None and query.partof is not None:
        search_params.partof = query.partof
    if search_params.sort is None and query.sort is not None:
        search_params.sort = query.sort

    effective_limit = search_params.limit if ("_count" in raw_dict or "limit" in raw_dict or "_count" in request.query_params) else (query.count if query.count is not None else (query.limit if query.limit is not None else 50))
    effective_offset = search_params.offset if ("_offset" in raw_dict or "offset" in raw_dict or "_offset" in request.query_params) else (query.offset_param if query.offset_param is not None else (query.offset if query.offset is not None else 0))
    search_params.limit = effective_limit
    search_params.offset = effective_offset

    orgs, total = await service.list_organizations(
        params=search_params,
        limit=effective_limit,
        offset=effective_offset,
    )
    return format_paginated_response(
        [service.to_fhir(o) for o in orgs],
        [service.to_plain(o) for o in orgs],
        total,
        effective_limit,
        effective_offset,
        request,
    )


def _parse_numeric_id(id_val: int | str) -> int:
    if isinstance(id_val, int):
        return id_val
    if isinstance(id_val, str) and id_val.strip().isdigit():
        return int(id_val.strip())
    raise NotFoundError(f"Organization '{id_val}' not found")


@router.get(
    "/{organization_id}",
    operation_id="get_organization_by_id",
    summary="Retrieve an Organization resource by public organization_id",
    responses={**_SINGLE_200, **_ERR_NOT_FOUND},
)
async def get_organization(
    organization_id: str,
    request: Request,
    actor: AuthUser = Depends(require_permission("organization", "read")),
    service: OrganizationService = Depends(get_organization_service),
):
    numeric_id = _parse_numeric_id(organization_id)
    logger.info(
        "Retrieve an Organization resource by public organization_id",
        extra={"event": "route.get_organization_by_id", "organization_id": numeric_id},
    )
    org = await service.get_organization(numeric_id)
    return format_response(service.to_fhir(org), service.to_plain(org), request)


@router.patch(
    "/{organization_id}",
    operation_id="patch_organization",
    summary="Partially update an Organization resource",
    description="Only supplied fields are written; omitted fields are left unchanged. Re-validates "
    "the full resulting FHIR resource before persisting. updated_by comes from the verified JWT's "
    "`sub` claim. " + _CONTENT_NEG,
    responses={**_SINGLE_200, **_ERR_NOT_FOUND, **_ERR_VALIDATION},
)
async def patch_organization(
    organization_id: str,
    payload: OrganizationPatchSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("organization", "update")),
    service: OrganizationService = Depends(get_organization_service),
):
    numeric_id = _parse_numeric_id(organization_id)
    org = await service.patch_organization(numeric_id, payload, actor.sub)
    return format_response(service.to_fhir(org), service.to_plain(org), request)


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_organization",
    summary="Delete an Organization resource",
    responses={**_ERR_NOT_FOUND},
)
async def delete_organization(
    organization_id: str,
    actor: AuthUser = Depends(require_permission("organization", "delete")),
    service: OrganizationService = Depends(get_organization_service),
):
    numeric_id = _parse_numeric_id(organization_id)
    await service.delete_organization(numeric_id)
    return None
