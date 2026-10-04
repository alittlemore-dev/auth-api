import uuid
from dataclasses import dataclass
from datetime import datetime
from math import ceil

from core.api_tokens.exceptions import (
    ApiTokenInactiveError,
    ApiTokenNotFoundError,
    ApiTokenPasswordConfirmationError,
)
from core.api_tokens.generators import ApiTokenSecretGenerator
from core.api_tokens.schemas import ApiCredentialVerification, ApiToken, ApiTokenCreate
from core.api_tokens.services import ApiPermissionRegistry
from core.api_tokens.storages import ApiTokenStorage
from core.auth.exceptions import UnauthorizedError, UserNotFoundError
from core.auth.password_hashers import PasswordHasher
from core.schemas import Secret


@dataclass(frozen=True, slots=True, kw_only=True)
class ApiTokensUseCase:
    storage: ApiTokenStorage
    hasher: PasswordHasher
    generator: ApiTokenSecretGenerator
    registry: ApiPermissionRegistry

    async def list_tokens(self, *, username: str) -> list[ApiToken]:
        return await self.storage.list_tokens(username=username)

    async def create_token(
        self,
        *,
        username: str,
        password: Secret[str],
        params: ApiTokenCreate,
        now: datetime,
    ) -> ApiToken:
        try:
            user = await self.storage.get_user(username=username, lock=True)
        except UserNotFoundError as exc:
            raise UnauthorizedError from exc
        if not user.is_active:
            raise UnauthorizedError
        verified, _ = self.hasher.verify_password(
            plain_password=password.get_secret_value(),
            hashed_password=user.password_hash.get_secret_value(),
        )
        if not verified:
            raise ApiTokenPasswordConfirmationError
        params.validate(now=now, allowed_permissions=self.registry.codes_for(user=user))
        secret = self.generator.generate()
        return await self.storage.create_token(
            token=ApiToken(
                id=uuid.uuid4().hex,
                username=user.username,
                name=params.name.strip(),
                permissions=params.permissions,
                secret_hash=self.generator.hash_secret(secret=secret),
                secret=secret,
                created_at=now,
                expires_at=params.expires_at,
                last_used_at=None,
                revoked_at=None,
            )
        )

    async def reveal_token(
        self,
        *,
        username: str,
        token_id: str,
        password: Secret[str],
        now: datetime,
    ) -> Secret[str]:
        try:
            user = await self.storage.get_user(username=username, lock=True)
        except UserNotFoundError as exc:
            raise UnauthorizedError from exc
        if not user.is_active:
            raise UnauthorizedError
        verified, _ = self.hasher.verify_password(
            plain_password=password.get_secret_value(),
            hashed_password=user.password_hash.get_secret_value(),
        )
        if not verified:
            raise ApiTokenPasswordConfirmationError
        token = await self.storage.get_token(token_id=token_id, username=user.username)
        token.ensure_owned_by(user=user)
        try:
            token.ensure_active(now=now)
        except UnauthorizedError as exc:
            raise ApiTokenInactiveError from exc
        return token.secret

    async def revoke_token(self, *, username: str, token_id: str, now: datetime) -> ApiToken:
        user = await self.storage.get_user(username=username, lock=True)
        token = await self.storage.get_token(token_id=token_id, username=user.username)
        token.ensure_owned_by(user=user)
        return await self.storage.revoke_token(token_id=token.id, username=user.username, now=now)

    async def verify(self, *, secret: Secret[str], now: datetime) -> ApiCredentialVerification:
        try:
            token = await self.storage.get_token_by_hash(
                secret_hash=self.generator.hash_secret(secret=secret),
            )
            user = await self.storage.get_user(username=token.username)
        except (ApiTokenNotFoundError, UserNotFoundError) as exc:
            raise UnauthorizedError from exc
        token.ensure_active(now=now)
        if not user.is_active:
            raise UnauthorizedError
        await self.storage.touch_token(token_id=token.id, now=now)
        return ApiCredentialVerification(
            user=user,
            credential_id=token.id,
            permissions=token.permissions & self.registry.codes_for(user=user),
            valid_for_seconds=ceil((token.expires_at - now).total_seconds()),
        )
