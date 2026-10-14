from app.errors.base import ApplicationError
from app.errors.fhir_codes import IssueType


class DatabaseError(ApplicationError):
    def __init__(self, message: str = "Database operation failed", cause: Exception | None = None):
        super().__init__(
            name="DatabaseError",
            message=message,
            status_code=500,
            code="DATABASE_ERROR",
            # "The persistent store is unavailable" is a more specific,
            # correct description than the generic "exception" default.
            issue_type=IssueType.NO_STORE,
            cause=cause,
            is_operational=False,
        )
