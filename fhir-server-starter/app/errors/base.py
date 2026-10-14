from typing import Any, Dict, Optional

from app.errors.fhir_codes import IssueSeverity, IssueType


class ApplicationError(Exception):
    """Base of every application-raised error. `code` is this project's own
    internal identifier (logged, never sent to the client, free-form by
    design — e.g. "BUSINESS_RULE_VIOLATION"). `issue_type` is the real
    OperationOutcome.issue.code value actually sent to the client — a FHIR
    IssueType (app/errors/fhir_codes.py), not a free string, so a response
    can never drift from a real HL7 code. `details`, when given, is a FHIR
    CodeableConcept dict ({"coding": [...], "text": ...}) for a more
    specific structured sub-code than `issue_type` alone can carry."""

    def __init__(
        self,
        name: str,
        message: str,
        *,
        status_code: int = 500,
        code: str = "APPLICATION_ERROR",
        issue_type: IssueType = IssueType.EXCEPTION,
        severity: IssueSeverity = IssueSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        is_operational: bool = True,
    ):
        super().__init__(message)
        self.name = name
        self.message = message
        self.status_code = status_code
        self.code = code
        self.issue_type = issue_type
        self.severity = severity
        self.details = details
        self.metadata = metadata or {}
        self.cause = cause
        self.is_operational = is_operational
