from app.errors.base import ApplicationError
from app.errors.fhir_codes import IssueType


class InputValidationError(ApplicationError):
    """Raised for an application-level validation failure beyond plain
    Pydantic schema validation. `errors` is a list of `{"field", "message"}`
    dicts, each optionally carrying its own `"issue_type"` — falls back to
    DEFAULT_ISSUE_TYPE for any entry that doesn't specify one."""

    DEFAULT_ISSUE_TYPE = IssueType.INVALID

    def __init__(self, errors: list[dict]):
        super().__init__(
            name="InputValidationError",
            message="Input validation failed",
            status_code=400,
            code="INPUT_VALIDATION_ERROR",
            issue_type=self.DEFAULT_ISSUE_TYPE,
            metadata={"errors": errors},
        )
        self.errors = errors


class FhirValidationError(ApplicationError):
    """Raised when a payload, once converted to true FHIR JSON, fails base
    R4 validation (app/fhir/validation/base_r4.py). 422, not 400: the
    request body itself parsed and passed Pydantic's own schema — this is a
    semantic/structural FHIR violation one layer up. `errors` is a list of
    `{"field", "message"}` dicts, each optionally carrying its own
    `"issue_type"` (base_r4.py maps jsonschema's own failure keyword to a
    real IssueType per entry)."""

    DEFAULT_ISSUE_TYPE = IssueType.INVALID

    def __init__(self, errors: list[dict]):
        super().__init__(
            name="FhirValidationError",
            message="FHIR R4 validation failed",
            status_code=422,
            code="FHIR_VALIDATION_ERROR",
            issue_type=self.DEFAULT_ISSUE_TYPE,
            metadata={"errors": errors},
        )
        self.errors = errors
