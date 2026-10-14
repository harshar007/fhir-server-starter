"""Base-layer FHIR R4 structural validation — the only validation backend
in this starter kit (the full fhir-server project also has a Java-validator
sidecar option for enforcing real invariants/slicing against country/org
profiles; deliberately left out here to keep this starter focused).

Uses HL7's published `fhir.schema.json` (app/fhir/spec/) as an independent
oracle. This layer only catches what a JSON Schema can express: required
elements, cardinality (0..1 vs 0..*), primitive formats, and
required-binding enums. It does NOT catch invariants (cross-field rules,
e.g. "name or identifier required") — those need a real FHIR validator
(like the HL7 Java one), which this starter kit doesn't include.
"""

import json
from pathlib import Path

from jsonschema import Draft6Validator

from app.errors.fhir_codes import IssueType

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "spec" / "fhir.schema.json"
_FHIR_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_DEFINITIONS = _FHIR_SCHEMA["definitions"]

# jsonschema's own `ValidationError.validator` keyword -> the nearest real
# HL7 IssueType. Not exhaustive — unmapped keywords fall back to
# IssueType.INVALID in validate_base_r4() below, which is always a legal
# choice, just less specific.
_JSONSCHEMA_KEYWORD_TO_ISSUE_TYPE = {
    "required": IssueType.REQUIRED,
    "type": IssueType.VALUE,
    "pattern": IssueType.VALUE,
    "format": IssueType.VALUE,
    "minLength": IssueType.VALUE,
    "maxLength": IssueType.VALUE,
    "enum": IssueType.CODE_INVALID,
    "const": IssueType.VALUE,
    "additionalProperties": IssueType.STRUCTURE,
}

_validators: dict[str, Draft6Validator] = {}


def _validator_for(resource_type: str) -> Draft6Validator:
    """One Draft6Validator per resource type, built once and cached. Each
    wraps just that resource's own definition, plus the full shared
    `definitions` dict alongside it so every internal `#/definitions/...`
    $ref used by the resource (Identifier, CodeableConcept, Address, ...)
    still resolves within the same schema document."""
    validator = _validators.get(resource_type)
    if validator is None:
        if resource_type not in _DEFINITIONS:
            raise ValueError(f"No base R4 definition for resource type {resource_type!r}")
        schema = {
            "$schema": _FHIR_SCHEMA["$schema"],
            "definitions": _DEFINITIONS,
            "$ref": f"#/definitions/{resource_type}",
        }
        validator = Draft6Validator(schema)
        _validators[resource_type] = validator
    return validator


def validate_base_r4(resource_type: str, fhir_resource: dict) -> list[dict]:
    """Validates `fhir_resource` (a true FHIR JSON dict — e.g. a mapper's
    output, not the DB-shaped input schema) against HL7's base R4 JSON
    Schema for `resource_type`. Returns a list of
    `{"field": str, "message": str, "issue_type": IssueType}` dicts, sorted
    by path, empty when valid."""
    validator = _validator_for(resource_type)
    errors = [
        {
            "field": ".".join(str(p) for p in err.absolute_path) or "(root)",
            "message": err.message,
            "issue_type": _JSONSCHEMA_KEYWORD_TO_ISSUE_TYPE.get(err.validator, IssueType.INVALID),
        }
        for err in sorted(validator.iter_errors(fhir_resource), key=lambda e: list(e.absolute_path))
    ]
    return errors
