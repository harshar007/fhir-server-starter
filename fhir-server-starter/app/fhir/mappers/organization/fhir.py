"""Builds real FHIR R4 camelCase JSON for Organization from OrganizationV2Model's
JSONB-separated columns (address, telecom, identifier, type, contact, endpoint, alias).
"""


def fhir_identifier(identifiers: list[dict]) -> list[dict]:
    return [
        {k: v for k, v in {"system": i.get("system"), "value": i.get("value"), "use": i.get("use")}.items() if v is not None}
        for i in identifiers
    ]


def fhir_codeable_concept(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        coding = {
            k: v
            for k, v in {"system": item.get("system"), "code": item.get("code"), "display": item.get("display")}.items()
            if v is not None
        }
        entry: dict = {}
        if coding:
            entry["coding"] = [coding]
        if item.get("text"):
            entry["text"] = item["text"]
        result.append(entry)
    return result


def fhir_telecom(telecoms: list[dict]) -> list[dict]:
    return [
        {k: v for k, v in {"system": t.get("system"), "value": t.get("value"), "use": t.get("use")}.items() if v is not None}
        for t in telecoms
    ]


def fhir_address(addresses: list[dict]) -> list[dict]:
    result = []
    for a in addresses:
        entry = {}
        if a.get("use"):
            entry["use"] = a["use"]
        if a.get("line"):
            entry["line"] = a["line"]
        if a.get("city"):
            entry["city"] = a["city"]
        if a.get("state"):
            entry["state"] = a["state"]
        if a.get("postal_code"):
            entry["postalCode"] = a["postal_code"]
        if a.get("country"):
            entry["country"] = a["country"]
        result.append(entry)
    return result


def fhir_contact(contacts: list[dict]) -> list[dict]:
    result = []
    for c in contacts:
        entry: dict = {}
        if c.get("purpose"):
            entry["purpose"] = {"text": c["purpose"]}
        if c.get("name"):
            entry["name"] = {"text": c["name"]}
        if c.get("telecom"):
            entry["telecom"] = fhir_telecom(c["telecom"])
        result.append(entry)
    return result


def fhir_endpoint(endpoints: list[dict]) -> list[dict]:
    return [
        {k: v for k, v in {"reference": e.get("reference"), "type": e.get("type"), "display": e.get("display")}.items() if v is not None}
        for e in endpoints
    ]


def _build_part_of(part_of: dict | int | None, partof_id: int | None = None, partof_display: str | None = None) -> dict | None:
    if isinstance(part_of, dict):
        return {k: v for k, v in part_of.items() if v is not None}
    if isinstance(part_of, int):
        return {"reference": f"Organization/{part_of}"}
    if partof_id is not None:
        ref: dict = {"reference": f"Organization/{partof_id}"}
        if partof_display:
            ref["display"] = partof_display
        return ref
    return None


def _build_fhir_organization(organization_id: int | None, name: str, active: bool, data: dict | None) -> dict:
    data = data or {}
    part_of_val = _build_part_of(data.get("part_of"), data.get("partof_id"), data.get("partof_display"))
    result = {
        "resourceType": "Organization",
        "id": str(organization_id) if organization_id is not None else None,
        "active": active,
        "name": name,
        "alias": data.get("alias") or None,
        "identifier": fhir_identifier(data.get("identifier", [])) or None,
        "type": fhir_codeable_concept(data.get("type", [])) or None,
        "telecom": fhir_telecom(data.get("telecom", [])) or None,
        "address": fhir_address(data.get("address", [])) or None,
        "contact": fhir_contact(data.get("contact", [])) or None,
        "endpoint": fhir_endpoint(data.get("endpoint", [])) or None,
        "partOf": part_of_val,
    }
    # Strip None at the end — real FHIR JSON never emits a key with a null value.
    return {k: v for k, v in result.items() if v is not None}


def to_fhir_organization(model) -> dict:
    data = {
        "alias": model.alias,
        "identifier": model.identifier,
        "type": model.type,
        "telecom": model.telecom,
        "address": model.address,
        "contact": model.contact,
        "endpoint": model.endpoint,
        "part_of": model.part_of,
        "partof_id": model.partof_id,
        "partof_display": model.partof_display,
    }
    return _build_fhir_organization(model.organization_id, model.name, model.active, data)


def preview_fhir_organization(name: str, active: bool, fhir_data: dict) -> dict:
    return _build_fhir_organization(None, name, active, fhir_data)
