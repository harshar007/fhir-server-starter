from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.errors.base import ApplicationError
from app.errors.fhir_codes import IssueType
from app.errors.validation import FhirValidationError, InputValidationError

logger = get_logger(__name__)

# Pydantic v2's own ValidationError `type` string -> the nearest real HL7
# IssueType. Not exhaustive — anything unmapped falls back to
# IssueType.INVALID (the parent code), which is always a legal choice, just
# less specific. Mirrors app/fhir/validation/base_r4.py's own
# jsonschema-keyword-to-IssueType mapping, same gap, same pragmatic answer.
_PYDANTIC_TYPE_TO_ISSUE_TYPE = {
    "missing": IssueType.REQUIRED,
    "extra_forbidden": IssueType.STRUCTURE,
}


def _pydantic_issue_type(err: dict) -> IssueType:
    return _PYDANTIC_TYPE_TO_ISSUE_TYPE.get(err.get("type"), IssueType.INVALID)


def _base_log_payload(request: Request) -> dict:
    return {
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "client_ip": request.client.host if request.client else None,
    }


def _issue(
    severity: str,
    issue_type: IssueType,
    diagnostics: str | None = None,
    expression: list[str] | None = None,
    details: dict | None = None,
) -> dict:
    """Builds one OperationOutcome.issue entry — the one place that shape
    gets assembled, so every handler branch emits the same field set."""
    issue: dict = {"severity": severity, "code": issue_type.value}
    if details:
        issue["details"] = details
    if diagnostics:
        issue["diagnostics"] = diagnostics
    if expression:
        issue["expression"] = expression
    return issue


def _operation_outcome(status_code: int, issues: list[dict]) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"resourceType": "OperationOutcome", "issue": issues},
    )


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    payload = _base_log_payload(request)
    is_server_error = exc.status_code >= 500
    payload.update(
        {
            "error_name": exc.name,
            "error_code": exc.code,
            "issue_type": exc.issue_type.value,
            "status_code": exc.status_code,
        }
    )

    if isinstance(exc, InputValidationError):
        logger.info("Input validation failed", extra={**payload, "event": "error.input_validation"})
        return _operation_outcome(
            400,
            [
                _issue(
                    "error",
                    error.get("issue_type", InputValidationError.DEFAULT_ISSUE_TYPE),
                    diagnostics=error["message"],
                    expression=[error["field"]],
                    details=error.get("details"),
                )
                for error in exc.errors
            ],
        )

    if isinstance(exc, FhirValidationError):
        logger.info("FHIR base R4 validation failed", extra={**payload, "event": "error.fhir_validation"})
        return _operation_outcome(
            422,
            [
                _issue(
                    "error",
                    error.get("issue_type", FhirValidationError.DEFAULT_ISSUE_TYPE),
                    diagnostics=error["message"],
                    expression=[error["field"]],
                    details=error.get("details"),
                )
                for error in exc.errors
            ],
        )

    if exc.is_operational:
        logger.warning("Operational application error", extra={**payload, "event": "error.operational"})
    else:
        logger.error(
            "Non-operational application error",
            extra={**payload, "event": "error.non_operational"},
            exc_info=True,
        )

    return _operation_outcome(
        exc.status_code,
        [
            _issue(
                exc.severity.value,
                exc.issue_type,
                diagnostics="Internal server error" if is_server_error else exc.message,
                details=exc.details,
            )
        ],
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    payload = _base_log_payload(request)
    logger.info(
        "Request schema validation failed",
        extra={**payload, "event": "error.schema_validation", "errors": exc.errors()},
    )
    issues = [
        _issue(
            "error",
            _pydantic_issue_type(err),
            diagnostics=err["msg"],
            expression=[".".join(str(loc) for loc in err["loc"] if loc != "body")],
        )
        for err in exc.errors()
    ]
    return _operation_outcome(422, issues)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    payload = _base_log_payload(request)
    logger.warning(
        "HTTP exception raised",
        extra={**payload, "event": "error.http_exception", "status_code": exc.status_code},
    )
    status_to_issue = {
        400: IssueType.INVALID,
        401: IssueType.SECURITY,
        403: IssueType.FORBIDDEN,
        404: IssueType.NOT_FOUND,
        409: IssueType.CONFLICT,
        422: IssueType.PROCESSING,
        500: IssueType.EXCEPTION,
    }
    return _operation_outcome(
        exc.status_code,
        [_issue("error", status_to_issue.get(exc.status_code, IssueType.PROCESSING), diagnostics=str(exc.detail))],
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    payload = _base_log_payload(request)
    logger.critical(
        "Unhandled exception occurred",
        extra={**payload, "event": "error.unhandled", "error_type": type(exc).__name__},
        exc_info=True,
    )
    return _operation_outcome(500, [_issue("error", IssueType.EXCEPTION, diagnostics="Internal server error")])
