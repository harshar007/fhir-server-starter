from fastapi import APIRouter, Depends, Query, Request, status

from app.auth.models import AuthUser
from app.auth.rbac import require_permission
from app.core.content_negotiation import format_paginated_response, format_response
from app.core.logging import get_logger
from app.core.schema_utils import inline_schema
from app.di.dependencies.organization import get_organization_service
from app.schemas.organization import (
    FHIROrganizationBundle,
    FHIROrganizationSchema,
    OrganizationCreateSchema,
    OrganizationPatchSchema,
    PaginatedOrganizationResponse,
    PlainOrganizationResponse,
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


@router.get(
    "/{organization_id}",
    operation_id="get_organization_by_id",
    summary="Retrieve an Organization resource by public organization_id",
    responses={**_SINGLE_200, **_ERR_NOT_FOUND},
)
async def get_organization(
    organization_id: int,
    request: Request,
    actor: AuthUser = Depends(require_permission("organization", "read")),
    service: OrganizationService = Depends(get_organization_service),
):
    logger.info(
        "Retrieve an Organization resource by public organization_id",
        extra={"event": "route.get_organization_by_id", "organization_id": organization_id},
    )
    org = await service.get_organization(organization_id)
    return format_response(service.to_fhir(org), service.to_plain(org), request)


@router.get(
    "/",
    operation_id="list_organizations",
    summary="List Organization resources",
    responses=_LIST_200,
)
async def list_organizations(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    actor: AuthUser = Depends(require_permission("organization", "read")),
    service: OrganizationService = Depends(get_organization_service),
):
    orgs, total = await service.list_organizations(limit=limit, offset=offset)
    return format_paginated_response(
        [service.to_fhir(o) for o in orgs],
        [service.to_plain(o) for o in orgs],
        total,
        limit,
        offset,
        request,
    )


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
    organization_id: int,
    payload: OrganizationPatchSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("organization", "update")),
    service: OrganizationService = Depends(get_organization_service),
):
    org = await service.patch_organization(organization_id, payload, actor.sub)
    return format_response(service.to_fhir(org), service.to_plain(org), request)


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_organization",
    summary="Delete an Organization resource",
    responses={**_ERR_NOT_FOUND},
)
async def delete_organization(
    organization_id: int,
    actor: AuthUser = Depends(require_permission("organization", "delete")),
    service: OrganizationService = Depends(get_organization_service),
):
    await service.delete_organization(organization_id)
    return None
