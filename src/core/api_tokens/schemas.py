from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.api_tokens.exceptions import InvalidApiTokenError
from core.auth.exceptions import ForbiddenError, UnauthorizedError
from core.auth.schemas import User
from core.schemas import Secret


@dataclass(frozen=True, slots=True, kw_only=True)
class ApiPermission:
    code: str
    service: str
    domain: str
    action: str
    minimum_role: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ApiToken:
    id: str
    username: str
    name: str
    permissions: frozenset[str]
    secret_hash: str = field(repr=False)
    secret: Secret[str] = field(repr=False)
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

    def status_at(self, *, now: datetime) -> str:
        if self.revoked_at is not None:
            return "revoked"
        return "active" if self.expires_at > now else "expired"

    def ensure_active(self, *, now: datetime) -> None:
        if self.status_at(now=now) != "active":
            raise UnauthorizedError

    def ensure_owned_by(self, *, user: User) -> None:
        if self.username != user.username:
            raise ForbiddenError


API_TOKEN_NAME_MAX_LENGTH = 100


@dataclass(frozen=True, slots=True, kw_only=True)
class ApiTokenCreate:
    name: str
    permissions: frozenset[str]
    expires_at: datetime

    def validate(self, *, now: datetime, allowed_permissions: frozenset[str]) -> None:
        if (
            not self.name.strip()
            or len(self.name) > API_TOKEN_NAME_MAX_LENGTH
            or not self.permissions
            or not self.permissions <= allowed_permissions
            or self.expires_at.tzinfo is None
            or not now < self.expires_at <= now + timedelta(days=365)
        ):
            raise InvalidApiTokenError


@dataclass(frozen=True, slots=True, kw_only=True)
class ApiCredentialVerification:
    user: User
    credential_id: str
    permissions: frozenset[str]
    valid_for_seconds: int
