from __future__ import annotations

from app.core.logging import trace_methods
from app.errors.domain import NotFoundError
from app.errors.validation import FhirValidationError
from app.fhir.mappers.organization import (
    preview_fhir_organization,
    to_fhir_organization,
    to_plain_organization,
)
from app.fhir.validation.base_r4 import validate_base_r4
from app.models.organization import OrganizationModel
from app.repository.organization_repository import OrganizationRepository
from app.schemas.organization import (
    OrganizationCreateSchema,
    OrganizationPatchSchema,
    ReferenceSchema,
)


@trace_methods
class OrganizationService:
    """Thin orchestration between the router and OrganizationRepository.
    Owns the FHIR base R4 validation step: every create/patch validates a
    PREVIEW of the resulting FHIR resource (built from the payload, not
    yet persisted) before writing anything, so an invalid write never
    reaches the database — this is the one thing this class does beyond a
    pass-through."""

    def __init__(self, repository: OrganizationRepository):
        self.repository = repository

    @staticmethod
    def _parse_part_of(part_of: int | ReferenceSchema | dict | None) -> tuple[int | None, str | None, str | None, dict | None]:
        if part_of is None:
            return None, None, None, None
        if isinstance(part_of, int):
            return part_of, "Organization", None, {"reference": f"Organization/{part_of}"}
        
        part_dict = part_of.model_dump(exclude_none=True) if hasattr(part_of, "model_dump") else dict(part_of)
        partof_id = None
        ref = part_dict.get("reference", "")
        if ref.startswith("Organization/"):
            try:
                partof_id = int(ref.split("/")[1])
            except ValueError:
                pass
        partof_type = part_dict.get("type") or "Organization"
        partof_display = part_dict.get("display")
        return partof_id, partof_type, partof_display, part_dict

    @staticmethod
    async def _validate(fhir_resource: dict) -> None:
        """Raises FhirValidationError (422) if `fhir_resource` fails base
        R4 validation — see app/fhir/validation/base_r4.py."""
        errors = validate_base_r4("Organization", fhir_resource)
        if errors:
            raise FhirValidationError(errors)

    def to_fhir(self, model: OrganizationModel) -> dict:
        return to_fhir_organization(model)

    def to_plain(self, model: OrganizationModel) -> dict:
        return to_plain_organization(model)

    async def create_organization(
        self, payload: OrganizationCreateSchema, created_by: str | None, org_id: str | None = None
    ) -> OrganizationModel:
        effective_org_id = payload.org_id or org_id or "default"
        effective_created_by = created_by or "unknown"

        alias = payload.alias
        identifier = [i.model_dump(exclude_none=True) for i in payload.identifier]
        type_val = [t.model_dump(exclude_none=True) for t in payload.type]
        telecom = [t.model_dump(exclude_none=True) for t in payload.telecom]
        address = [a.model_dump(exclude_none=True) for a in payload.address]
        contact = [c.model_dump(exclude_none=True) for c in payload.contact]
        endpoint = [e.model_dump(exclude_none=True) for e in payload.endpoint]
        partof_id, partof_type, partof_display, part_of_json = self._parse_part_of(payload.part_of)

        preview_data = {
            "alias": alias,
            "identifier": identifier,
            "type": type_val,
            "telecom": telecom,
            "address": address,
            "contact": contact,
            "endpoint": endpoint,
            "part_of": part_of_json,
            "partof_id": partof_id,
            "partof_display": partof_display,
        }
        await self._validate(preview_fhir_organization(payload.name, payload.active, preview_data))

        return await self.repository.create(
            org_id=effective_org_id,
            name=payload.name,
            active=payload.active,
            alias=alias,
            identifier=identifier,
            type=type_val,
            telecom=telecom,
            address=address,
            contact=contact,
            endpoint=endpoint,
            part_of=part_of_json,
            partof_id=partof_id,
            partof_type=partof_type,
            partof_display=partof_display,
            created_by=effective_created_by,
        )

    async def get_organization(self, organization_id: int) -> OrganizationModel:
        org = await self.repository.get_by_organization_id(organization_id)
        if org is None:
            raise NotFoundError(f"Organization {organization_id} not found")
        return org

    async def list_organizations(self, *, limit: int, offset: int) -> tuple[list[OrganizationModel], int]:
        return await self.repository.list(limit=limit, offset=offset)

    async def patch_organization(
        self, organization_id: int, payload: OrganizationPatchSchema, updated_by: str | None
    ) -> OrganizationModel:
        existing = await self.get_organization(organization_id)

        name = payload.name if payload.name is not None else existing.name
        active = payload.active if payload.active is not None else existing.active

        alias = payload.alias if payload.alias is not None else existing.alias
        identifier = [i.model_dump(exclude_none=True) for i in payload.identifier] if payload.identifier is not None else existing.identifier
        type_val = [t.model_dump(exclude_none=True) for t in payload.type] if payload.type is not None else existing.type
        telecom = [t.model_dump(exclude_none=True) for t in payload.telecom] if payload.telecom is not None else existing.telecom
        address = [a.model_dump(exclude_none=True) for a in payload.address] if payload.address is not None else existing.address
        contact = [c.model_dump(exclude_none=True) for c in payload.contact] if payload.contact is not None else existing.contact
        endpoint = [e.model_dump(exclude_none=True) for e in payload.endpoint] if payload.endpoint is not None else existing.endpoint

        if payload.part_of is not None:
            partof_id, partof_type, partof_display, part_of_json = self._parse_part_of(payload.part_of)
        else:
            partof_id = existing.partof_id
            partof_type = existing.partof_type
            partof_display = existing.partof_display
            part_of_json = existing.part_of

        preview_data = {
            "alias": alias,
            "identifier": identifier,
            "type": type_val,
            "telecom": telecom,
            "address": address,
            "contact": contact,
            "endpoint": endpoint,
            "part_of": part_of_json,
            "partof_id": partof_id,
            "partof_display": partof_display,
        }
        await self._validate(preview_fhir_organization(name, active, preview_data))

        updated = await self.repository.patch(
            organization_id,
            name=payload.name,
            active=payload.active,
            alias=payload.alias,
            identifier=[i.model_dump(exclude_none=True) for i in payload.identifier] if payload.identifier is not None else None,
            type=[t.model_dump(exclude_none=True) for t in payload.type] if payload.type is not None else None,
            telecom=[t.model_dump(exclude_none=True) for t in payload.telecom] if payload.telecom is not None else None,
            address=[a.model_dump(exclude_none=True) for a in payload.address] if payload.address is not None else None,
            contact=[c.model_dump(exclude_none=True) for c in payload.contact] if payload.contact is not None else None,
            endpoint=[e.model_dump(exclude_none=True) for e in payload.endpoint] if payload.endpoint is not None else None,
            part_of=part_of_json if payload.part_of is not None else None,
            partof_id=partof_id if payload.part_of is not None else None,
            partof_type=partof_type if payload.part_of is not None else None,
            partof_display=partof_display if payload.part_of is not None else None,
            updated_by=updated_by,
        )
        if updated is None:
            raise NotFoundError(f"Organization {organization_id} not found")
        return updated

    async def delete_organization(self, organization_id: int) -> None:
        deleted = await self.repository.delete(organization_id)
        if not deleted:
            raise NotFoundError(f"Organization {organization_id} not found")
