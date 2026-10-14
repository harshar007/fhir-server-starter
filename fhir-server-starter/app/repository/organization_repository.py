from __future__ import annotations

from sqlalchemy import func, select

from app.models.organization import OrganizationModel
from app.repository.base import BaseRepository


class OrganizationRepository(BaseRepository):
    """session_factory/__init__ inherited from BaseRepository."""

    async def create(
        self,
        *,
        org_id: str,
        name: str,
        active: bool,
        alias: list,
        identifier: list,
        type: list,
        telecom: list,
        address: list,
        contact: list,
        endpoint: list,
        part_of: dict | None = None,
        partof_id: int | None = None,
        partof_type: str | None = None,
        partof_display: str | None = None,
        created_by: str,
    ) -> OrganizationModel:
        async with self.session_factory() as session:
            org = OrganizationModel(
                org_id=org_id,
                name=name,
                active=active,
                alias=alias,
                identifier=identifier,
                type=type,
                telecom=telecom,
                address=address,
                contact=contact,
                endpoint=endpoint,
                part_of=part_of,
                partof_id=partof_id,
                partof_type=partof_type,
                partof_display=partof_display,
                created_by=created_by,
                updated_by=created_by,
            )
            session.add(org)
            await session.commit()
            await session.refresh(org)
            return org

    async def get_by_organization_id(self, organization_id: int) -> OrganizationModel | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(OrganizationModel).where(OrganizationModel.organization_id == organization_id)
            )
            return result.scalar_one_or_none()

    async def list(self, *, limit: int, offset: int) -> tuple[list[OrganizationModel], int]:
        async with self.session_factory() as session:
            stmt = select(OrganizationModel)
            count_stmt = select(func.count()).select_from(OrganizationModel)
            rows, total = await self._execute_paginated(
                session,
                stmt,
                count_stmt,
                sort_column=OrganizationModel.id,
                sort_desc=True,
                limit=limit,
                offset=offset,
            )
            return list(rows), total or 0

    async def patch(
        self,
        organization_id: int,
        *,
        name: str | None = None,
        active: bool | None = None,
        alias: list | None = None,
        identifier: list | None = None,
        type: list | None = None,
        telecom: list | None = None,
        address: list | None = None,
        contact: list | None = None,
        endpoint: list | None = None,
        part_of: dict | None = None,
        partof_id: int | None = None,
        partof_type: str | None = None,
        partof_display: str | None = None,
        updated_by: str | None = None,
    ) -> OrganizationModel | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(OrganizationModel).where(OrganizationModel.organization_id == organization_id)
            )
            org = result.scalar_one_or_none()
            if org is None:
                return None
            if name is not None:
                org.name = name
            if active is not None:
                org.active = active
            if alias is not None:
                org.alias = alias
            if identifier is not None:
                org.identifier = identifier
            if type is not None:
                org.type = type
            if telecom is not None:
                org.telecom = telecom
            if address is not None:
                org.address = address
            if contact is not None:
                org.contact = contact
            if endpoint is not None:
                org.endpoint = endpoint
            if part_of is not None:
                org.part_of = part_of
            if partof_id is not None:
                org.partof_id = partof_id
            if partof_type is not None:
                org.partof_type = partof_type
            if partof_display is not None:
                org.partof_display = partof_display
            org.updated_by = updated_by
            await session.commit()
            await session.refresh(org)
            return org

    async def delete(self, organization_id: int) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(
                select(OrganizationModel).where(OrganizationModel.organization_id == organization_id)
            )
            org = result.scalar_one_or_none()
            if org is None:
                return False
            await session.delete(org)
            await session.commit()
            return True
