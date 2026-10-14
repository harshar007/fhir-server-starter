from __future__ import annotations

from sqlalchemy import and_, cast, func, or_, select, String

from app.models.organization import OrganizationModel
from app.repository.base import BaseRepository
from app.schemas.organization import OrganizationSearchParams


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

    def _build_search_filters(self, params: OrganizationSearchParams) -> list:
        filters = []

        # 1. _id (logical id, maps to organization_id)
        if params._id is not None:
            ids = [int(x.strip()) for x in params._id.split(",") if x.strip().isdigit()]
            if ids:
                filters.append(OrganizationModel.organization_id.in_(ids))
        elif params._id_missing is not None:
            if params._id_missing:
                filters.append(OrganizationModel.organization_id.is_(None))
            else:
                filters.append(OrganizationModel.organization_id.is_not(None))

        # 2. active
        if params.active is not None:
            val = params.active.strip().lower()
            if val in ("true", "1"):
                filters.append(OrganizationModel.active.is_(True))
            elif val in ("false", "0"):
                filters.append(OrganizationModel.active.is_(False))
        elif params.active_missing is not None:
            if params.active_missing:
                filters.append(OrganizationModel.active.is_(None))
            else:
                filters.append(OrganizationModel.active.is_not(None))

        # 3. name (name or alias)
        if params.name is not None:
            n = params.name.strip()
            if params.name_exact:
                filters.append(or_(
                    OrganizationModel.name == n,
                    cast(OrganizationModel.alias, String).ilike(f'%"{n}"%')
                ))
            else:
                filters.append(or_(
                    OrganizationModel.name.ilike(f"%{n}%"),
                    cast(OrganizationModel.alias, String).ilike(f"%{n}%")
                ))
        elif params.name_missing is not None:
            if params.name_missing:
                filters.append(or_(OrganizationModel.name.is_(None), OrganizationModel.name == ""))
            else:
                filters.append(and_(OrganizationModel.name.is_not(None), OrganizationModel.name != ""))

        # 4. phonetic (name)
        if params.phonetic is not None:
            p = params.phonetic.strip()
            filters.append(OrganizationModel.name.ilike(f"%{p}%"))
        elif params.phonetic_missing is not None:
            if params.phonetic_missing:
                filters.append(or_(OrganizationModel.name.is_(None), OrganizationModel.name == ""))
            else:
                filters.append(and_(OrganizationModel.name.is_not(None), OrganizationModel.name != ""))

        # 5. identifier (token)
        if params.identifier is not None:
            token_clauses = []
            for token in params.identifier.split(","):
                token = token.strip()
                if not token:
                    continue
                if "|" in token:
                    system, code = token.split("|", 1)
                    sub = []
                    if system:
                        sub.append(cast(OrganizationModel.identifier, String).ilike(f'%"{system}"%'))
                    if code:
                        sub.append(cast(OrganizationModel.identifier, String).ilike(f'%"{code}"%'))
                    if sub:
                        token_clauses.append(and_(*sub))
                else:
                    token_clauses.append(cast(OrganizationModel.identifier, String).ilike(f'%"{token}"%'))
            if token_clauses:
                filters.append(or_(*token_clauses))
        elif params.identifier_missing is not None:
            if params.identifier_missing:
                filters.append(or_(OrganizationModel.identifier.is_(None), cast(OrganizationModel.identifier, String).in_(["null", "[]", ""])))
            else:
                filters.append(and_(OrganizationModel.identifier.is_not(None), ~cast(OrganizationModel.identifier, String).in_(["null", "[]", ""])))

        # 6. type (token)
        if params.type is not None:
            type_clauses = []
            for token in params.type.split(","):
                token = token.strip()
                if not token:
                    continue
                if "|" in token:
                    system, code = token.split("|", 1)
                    sub = []
                    if system:
                        sub.append(cast(OrganizationModel.type, String).ilike(f'%"{system}"%'))
                    if code:
                        sub.append(cast(OrganizationModel.type, String).ilike(f'%"{code}"%'))
                    if sub:
                        type_clauses.append(and_(*sub))
                else:
                    type_clauses.append(or_(
                        cast(OrganizationModel.type, String).ilike(f'%"{token}"%'),
                        cast(OrganizationModel.type, String).ilike(f'%"code": "%{token}%"%'),
                        cast(OrganizationModel.type, String).ilike(f'%"display": "%{token}%"%')
                    ))
            if type_clauses:
                filters.append(or_(*type_clauses))
        elif params.type_missing is not None:
            if params.type_missing:
                filters.append(or_(OrganizationModel.type.is_(None), cast(OrganizationModel.type, String).in_(["null", "[]", ""])))
            else:
                filters.append(and_(OrganizationModel.type.is_not(None), ~cast(OrganizationModel.type, String).in_(["null", "[]", ""])))

        # 7. address (general address string match)
        if params.address is not None:
            addr_clauses = []
            for term in params.address.split(","):
                term = term.strip()
                if term:
                    addr_clauses.append(cast(OrganizationModel.address, String).ilike(f"%{term}%"))
            if addr_clauses:
                filters.append(or_(*addr_clauses))
        elif params.address_missing is not None:
            if params.address_missing:
                filters.append(or_(OrganizationModel.address.is_(None), cast(OrganizationModel.address, String).in_(["null", "[]", ""])))
            else:
                filters.append(and_(OrganizationModel.address.is_not(None), ~cast(OrganizationModel.address, String).in_(["null", "[]", ""])))

        # 8. address-city
        if params.address_city is not None:
            city_clauses = []
            for term in params.address_city.split(","):
                term = term.strip()
                if term:
                    city_clauses.append(or_(
                        cast(OrganizationModel.address, String).ilike(f'%"city": "%{term}%"%'),
                        cast(OrganizationModel.address, String).ilike(f'%"city":"%{term}%"%')
                    ))
            if city_clauses:
                filters.append(or_(*city_clauses))
        elif params.address_city_missing is not None:
            if params.address_city_missing:
                filters.append(or_(OrganizationModel.address.is_(None), ~cast(OrganizationModel.address, String).ilike('%"city"%')))
            else:
                filters.append(and_(OrganizationModel.address.is_not(None), cast(OrganizationModel.address, String).ilike('%"city"%')))

        # 9. address-state
        if params.address_state is not None:
            state_clauses = []
            for term in params.address_state.split(","):
                term = term.strip()
                if term:
                    state_clauses.append(or_(
                        cast(OrganizationModel.address, String).ilike(f'%"state": "%{term}%"%'),
                        cast(OrganizationModel.address, String).ilike(f'%"state":"%{term}%"%')
                    ))
            if state_clauses:
                filters.append(or_(*state_clauses))
        elif params.address_state_missing is not None:
            if params.address_state_missing:
                filters.append(or_(OrganizationModel.address.is_(None), ~cast(OrganizationModel.address, String).ilike('%"state"%')))
            else:
                filters.append(and_(OrganizationModel.address.is_not(None), cast(OrganizationModel.address, String).ilike('%"state"%')))

        # 10. address-postalcode
        if params.address_postalcode is not None:
            pc_clauses = []
            for term in params.address_postalcode.split(","):
                term = term.strip()
                if term:
                    pc_clauses.append(or_(
                        cast(OrganizationModel.address, String).ilike(f'%"postal_code": "%{term}%"%'),
                        cast(OrganizationModel.address, String).ilike(f'%"postal_code":"%{term}%"%'),
                        cast(OrganizationModel.address, String).ilike(f'%"postalCode": "%{term}%"%'),
                        cast(OrganizationModel.address, String).ilike(f'%"postalCode":"%{term}%"%')
                    ))
            if pc_clauses:
                filters.append(or_(*pc_clauses))
        elif params.address_postalcode_missing is not None:
            if params.address_postalcode_missing:
                filters.append(or_(
                    OrganizationModel.address.is_(None),
                    and_(
                        ~cast(OrganizationModel.address, String).ilike('%"postal_code"%'),
                        ~cast(OrganizationModel.address, String).ilike('%"postalCode"%')
                    )
                ))
            else:
                filters.append(and_(
                    OrganizationModel.address.is_not(None),
                    or_(
                        cast(OrganizationModel.address, String).ilike('%"postal_code"%'),
                        cast(OrganizationModel.address, String).ilike('%"postalCode"%')
                    )
                ))

        # 11. address-country
        if params.address_country is not None:
            c_clauses = []
            for term in params.address_country.split(","):
                term = term.strip()
                if term:
                    c_clauses.append(or_(
                        cast(OrganizationModel.address, String).ilike(f'%"country": "%{term}%"%'),
                        cast(OrganizationModel.address, String).ilike(f'%"country":"%{term}%"%')
                    ))
            if c_clauses:
                filters.append(or_(*c_clauses))
        elif params.address_country_missing is not None:
            if params.address_country_missing:
                filters.append(or_(OrganizationModel.address.is_(None), ~cast(OrganizationModel.address, String).ilike('%"country"%')))
            else:
                filters.append(and_(OrganizationModel.address.is_not(None), cast(OrganizationModel.address, String).ilike('%"country"%')))

        # 12. address-use
        if params.address_use is not None:
            u_clauses = []
            for term in params.address_use.split(","):
                term = term.strip()
                if term:
                    u_clauses.append(or_(
                        cast(OrganizationModel.address, String).ilike(f'%"use": "%{term}%"%'),
                        cast(OrganizationModel.address, String).ilike(f'%"use":"%{term}%"%')
                    ))
            if u_clauses:
                filters.append(or_(*u_clauses))
        elif params.address_use_missing is not None:
            if params.address_use_missing:
                filters.append(or_(OrganizationModel.address.is_(None), ~cast(OrganizationModel.address, String).ilike('%"use"%')))
            else:
                filters.append(and_(OrganizationModel.address.is_not(None), cast(OrganizationModel.address, String).ilike('%"use"%')))

        # 13. endpoint
        if params.endpoint is not None:
            ep_clauses = []
            for term in params.endpoint.split(","):
                term = term.strip()
                if term:
                    ep_clauses.append(cast(OrganizationModel.endpoint, String).ilike(f"%{term}%"))
            if ep_clauses:
                filters.append(or_(*ep_clauses))
        elif params.endpoint_missing is not None:
            if params.endpoint_missing:
                filters.append(or_(OrganizationModel.endpoint.is_(None), cast(OrganizationModel.endpoint, String).in_(["null", "[]", ""])))
            else:
                filters.append(and_(OrganizationModel.endpoint.is_not(None), ~cast(OrganizationModel.endpoint, String).in_(["null", "[]", ""])))

        # 14. partof
        if params.partof is not None:
            po_clauses = []
            for term in params.partof.split(","):
                term = term.strip()
                if not term:
                    continue
                digits = term.split("/")[-1] if "/" in term else term
                if digits.isdigit():
                    po_clauses.append(OrganizationModel.partof_id == int(digits))
                po_clauses.append(cast(OrganizationModel.part_of, String).ilike(f"%{term}%"))
                po_clauses.append(OrganizationModel.partof_display.ilike(f"%{term}%"))
            if po_clauses:
                filters.append(or_(*po_clauses))
        elif params.partof_missing is not None:
            if params.partof_missing:
                filters.append(or_(
                    OrganizationModel.partof_id.is_(None),
                    cast(OrganizationModel.part_of, String).in_([None, "null", "", "{}"])
                ))
            else:
                filters.append(or_(
                    OrganizationModel.partof_id.is_not(None),
                    and_(OrganizationModel.part_of.is_not(None), ~cast(OrganizationModel.part_of, String).in_(["null", "", "{}"]))
                ))

        return filters

    async def list(
        self,
        *,
        params: OrganizationSearchParams | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OrganizationModel], int]:
        async with self.session_factory() as session:
            stmt = select(OrganizationModel)
            count_stmt = select(func.count()).select_from(OrganizationModel)

            effective_limit = params.limit if params else limit
            effective_offset = params.offset if params else offset

            sort_col = OrganizationModel.id
            sort_desc = True

            if params:
                filters = self._build_search_filters(params)
                if filters:
                    stmt = stmt.where(and_(*filters))
                    count_stmt = count_stmt.where(and_(*filters))

                if params.sort:
                    sort_field = params.sort.strip()
                    desc = sort_field.startswith("-")
                    clean_field = sort_field.lstrip("+-")
                    if clean_field in ("id", "_id", "organization_id"):
                        sort_col = OrganizationModel.organization_id
                        sort_desc = desc
                    elif clean_field == "name":
                        sort_col = OrganizationModel.name
                        sort_desc = desc
                    elif clean_field == "active":
                        sort_col = OrganizationModel.active
                        sort_desc = desc

            rows, total = await self._execute_paginated(
                session,
                stmt,
                count_stmt,
                sort_column=sort_col,
                sort_desc=sort_desc,
                limit=effective_limit,
                offset=effective_offset,
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
