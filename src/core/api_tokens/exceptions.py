from core.auth.exceptions import ForbiddenError
from core.exceptions import DomainError, EntryNotFoundError


class ApiTokenNotFoundError(EntryNotFoundError):
    message = "API token not found"


class InvalidApiTokenError(DomainError):
    message = "Invalid API token name, permissions or expiration"


class ApiTokenPasswordConfirmationError(ForbiddenError):
    message = "Current-password confirmation failed"


class ApiTokenInactiveError(ForbiddenError):
    message = "API token is inactive"
