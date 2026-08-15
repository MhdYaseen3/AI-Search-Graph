from typing import Any


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(message, status_code=404, **kwargs)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", **kwargs: Any) -> None:
        super().__init__(message, status_code=422, **kwargs)


class ExternalServiceError(AppException):
    def __init__(
        self,
        message: str = "External service error",
        *,
        service: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if service:
            details["service"] = service
        super().__init__(message, status_code=502, details=details, **kwargs)


class DatabaseError(AppException):
    def __init__(self, message: str = "Database operation failed", **kwargs: Any) -> None:
        super().__init__(message, status_code=503, **kwargs)
