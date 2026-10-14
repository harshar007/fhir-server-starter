"""Builds the simplified snake_case JSON for Organization — the
`application/json` side of this starter's dual content-negotiation
(app/core/content_negotiation.py).
"""


def to_plain_organization(model) -> dict:
    part_of_id = model.partof_id
    if part_of_id is None and isinstance(model.part_of, dict):
        ref = model.part_of.get("reference", "")
        if ref.startswith("Organization/"):
            try:
                part_of_id = int(ref.split("/")[1])
            except ValueError:
                pass

    return {
        "id": model.organization_id,
        "org_id": model.org_id,
        "name": model.name,
        "active": model.active,
        "identifier": model.identifier or [],
        "type": model.type or [],
        "alias": model.alias or [],
        "telecom": model.telecom or [],
        "address": model.address or [],
        "contact": model.contact or [],
        "endpoint": model.endpoint or [],
        "part_of": part_of_id,
        "partof_id": model.partof_id,
        "partof_display": model.partof_display,
        "created_by": model.created_by,
        "updated_by": model.updated_by,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }
