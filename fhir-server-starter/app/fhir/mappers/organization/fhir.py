"""Builds real FHIR R4 camelCase JSON for Organization from OrganizationV2Model's
JSONB-separated columns (address, telecom, identifier, type, contact, endpoint, alias).
Follows HL7 FHIR R4 Organization specification:
https://www.hl7.org/fhir/R4/organization.html
"""
from __future__ import annotations


def fhir_identifier(identifiers: list[dict]) -> list[dict]:
    result = []
    for i in identifiers:
        entry = {}
        if i.get("use"):
            entry["use"] = i["use"]
        if i.get("type"):
            if isinstance(i["type"], dict):
                entry["type"] = fhir_codeable_concept([i["type"]])[0] if "coding" not in i["type"] and "text" not in i["type"] else i["type"]
            else:
                entry["type"] = {"text": str(i["type"])}
        if i.get("system"):
            entry["system"] = i["system"]
        if i.get("value"):
            entry["value"] = i["value"]
        if i.get("period"):
            entry["period"] = i["period"]
        if i.get("assigner"):
            entry["assigner"] = i["assigner"]
        if entry:
            result.append(entry)
    return result


def fhir_codeable_concept(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        entry: dict = {}
        if item.get("coding"):
            entry["coding"] = item["coding"]
        else:
            coding = {
                k: v
                for k, v in {
                    "system": item.get("system"),
                    "version": item.get("version"),
                    "code": item.get("code"),
                    "display": item.get("display"),
                    "userSelected": item.get("userSelected"),
                }.items()
                if v is not None
            }
            if coding:
                entry["coding"] = [coding]
        if item.get("text"):
            entry["text"] = item["text"]
        if entry:
            result.append(entry)
    return result


def fhir_telecom(telecoms: list[dict]) -> list[dict]:
    result = []
    for t in telecoms:
        entry = {}
        if t.get("system"):
            entry["system"] = t["system"]
        if t.get("value"):
            entry["value"] = t["value"]
        if t.get("use"):
            entry["use"] = t["use"]
        if t.get("rank") is not None:
            entry["rank"] = t["rank"]
        if t.get("period"):
            entry["period"] = t["period"]
        if entry:
            result.append(entry)
    return result


def fhir_address(addresses: list[dict]) -> list[dict]:
    result = []
    for a in addresses:
        entry = {}
        if a.get("use"):
            entry["use"] = a["use"]
        if a.get("type"):
            entry["type"] = a["type"]
        if a.get("text"):
            entry["text"] = a["text"]
        if a.get("line"):
            entry["line"] = a["line"]
        if a.get("city"):
            entry["city"] = a["city"]
        if a.get("district"):
            entry["district"] = a["district"]
        if a.get("state"):
            entry["state"] = a["state"]
        postal_code = a.get("postal_code") or a.get("postalCode")
        if postal_code:
            entry["postalCode"] = postal_code
        if a.get("country"):
            entry["country"] = a["country"]
        if a.get("period"):
            entry["period"] = a["period"]
        if entry:
            result.append(entry)
    return result


def fhir_human_name(names: list[dict | str]) -> list[dict]:
    result = []
    for n in names:
        if isinstance(n, str):
            result.append({"text": n})
        elif isinstance(n, dict):
            entry = {}
            for k in ("use", "text", "family", "given", "prefix", "suffix", "period"):
                if n.get(k) is not None:
                    entry[k] = n[k]
            if entry:
                result.append(entry)
    return result


def fhir_contact(contacts: list[dict]) -> list[dict]:
    result = []
    for c in contacts:
        entry: dict = {}
        if c.get("purpose"):
            if isinstance(c["purpose"], dict):
                entry["purpose"] = fhir_codeable_concept([c["purpose"]])[0] if "coding" not in c["purpose"] and "text" not in c["purpose"] else c["purpose"]
            else:
                entry["purpose"] = {"text": c["purpose"]}
        if c.get("name"):
            if isinstance(c["name"], dict):
                entry["name"] = fhir_human_name([c["name"]])[0]
            else:
                entry["name"] = {"text": c["name"]}
        if c.get("telecom"):
            entry["telecom"] = fhir_telecom(c["telecom"])
        if c.get("address"):
            addr = c["address"]
            entry["address"] = fhir_address([addr])[0] if isinstance(addr, dict) else addr
        if entry:
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


def _build_fhir_organization(
    organization_id: int | None,
    name: str,
    active: bool,
    data: dict | None,
    created_at=None,
    updated_at=None,
) -> dict:
    data = data or {}
    part_of_val = _build_part_of(data.get("part_of"), data.get("partof_id"), data.get("partof_display"))

    # Build meta
    meta = data.get("meta")
    if not meta and (created_at or updated_at):
        ts = updated_at or created_at
        timestamp = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        meta = {"versionId": "1", "lastUpdated": timestamp}

    result = {
        "resourceType": "Organization",
        "id": str(organization_id) if organization_id is not None else None,
        "meta": meta or None,
        "implicitRules": data.get("implicitRules") or None,
        "language": data.get("language") or None,
        "text": data.get("text") or None,
        "contained": data.get("contained") or None,
        "extension": data.get("extension") or None,
        "modifierExtension": data.get("modifierExtension") or None,
        "identifier": fhir_identifier(data.get("identifier", [])) or None,
        "active": active,
        "type": fhir_codeable_concept(data.get("type", [])) or None,
        "name": name,
        "alias": data.get("alias") or None,
        "telecom": fhir_telecom(data.get("telecom", [])) or None,
        "address": fhir_address(data.get("address", [])) or None,
        "partOf": part_of_val,
        "contact": fhir_contact(data.get("contact", [])) or None,
        "endpoint": fhir_endpoint(data.get("endpoint", [])) or None,
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
    return _build_fhir_organization(
        model.organization_id,
        model.name,
        model.active,
        data,
        created_at=getattr(model, "created_at", None),
        updated_at=getattr(model, "updated_at", None),
    )


def preview_fhir_organization(name: str, active: bool, fhir_data: dict) -> dict:
    return _build_fhir_organization(None, name, active, fhir_data)
