"""Domain-level exception hierarchy.

Services and repositories raise these instead of ``HTTPException`` so that
business logic stays framework-agnostic. A single handler in the API layer
translates them to HTTP responses (registered in ``app.main``).
"""


class AppError(Exception):
    """Base class for all expected application errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """A requested entity does not exist. Maps to HTTP 404."""


class ConflictError(AppError):
    """The request conflicts with existing state (e.g. duplicate email). Maps to HTTP 409."""


class UnauthorizedError(AppError):
    """Authentication failed or is missing. Maps to HTTP 401."""


class ForbiddenError(AppError):
    """The authenticated user may not perform this action. Maps to HTTP 403."""
