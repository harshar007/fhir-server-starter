from app.errors.base import ApplicationError
from app.errors.fhir_codes import IssueType


class AuthenticationError(ApplicationError):
    """Always 401; never reveals which specific failure mode occurred —
    issue_type stays the parent `security` code deliberately, not a more
    specific child like `login`/`expired`/`unknown`."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            name="AuthenticationError",
            message=message,
            status_code=401,
            code="AUTHENTICATION_ERROR",
            issue_type=IssueType.SECURITY,
        )


class PermissionDeniedError(ApplicationError):
    """Always 403 — distinct from AuthenticationError's 401, since the
    caller's identity is known here, just insufficiently privileged."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            name="PermissionDeniedError",
            message=message,
            status_code=403,
            code="PERMISSION_DENIED",
            issue_type=IssueType.FORBIDDEN,
        )
