import hashlib
from dataclasses import dataclass

from litestar.stores.base import Store

from core.auth.storages import TokenRevocationStorage
from core.auth.types import Token


@dataclass(kw_only=True, slots=True, frozen=True)
class ValkeyTokenRevocationStorage(TokenRevocationStorage):
    store: Store

    async def revoke_token(self, token: Token, expires_in_seconds: int) -> None:
        await self.store.set(
            key=self._token_key(token),
            value=b"revoked",
            expires_in=expires_in_seconds,
        )

    async def is_token_revoked(self, token: Token) -> bool:
        return await self.store.exists(key=self._token_key(token))

    def _token_key(self, token: Token) -> str:
        return hashlib.sha256(token).hexdigest()
