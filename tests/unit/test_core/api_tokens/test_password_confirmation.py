from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from core.api_tokens.exceptions import ApiTokenInactiveError, ApiTokenPasswordConfirmationError
from core.api_tokens.generators import ApiTokenSecretGenerator
from core.api_tokens.schemas import ApiToken, ApiTokenCreate
from core.api_tokens.services import ApiPermissionRegistry
from core.api_tokens.storages import ApiTokenStorage
from core.api_tokens.use_cases import ApiTokensUseCase
from core.auth.exceptions import UnauthorizedError, UserNotFoundError
from core.auth.password_hashers import PasswordHasher
from core.schemas import Secret
from tests.test_cases import TestCase


class TestApiTokenPasswordConfirmation(TestCase):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.now = datetime(2026, 10, 4, tzinfo=UTC)
        self.storage = Mock(spec=ApiTokenStorage)
        self.storage.get_user.return_value = self.factory.core.user(username="owner")
        self.hasher = Mock(spec=PasswordHasher)
        self.hasher.verify_password.return_value = False, False
        self.use_case = ApiTokensUseCase(
            storage=self.storage,
            hasher=self.hasher,
            generator=ApiTokenSecretGenerator(),
            registry=ApiPermissionRegistry(),
        )

    async def confirm_password(self, *, operation: str) -> None:
        if operation == "create":
            await self.use_case.create_token(
                username="owner",
                password=Secret("incorrect"),
                now=self.now,
                params=ApiTokenCreate(
                    name="CLI",
                    permissions=frozenset({"auth.account.read"}),
                    expires_at=self.now + timedelta(hours=1),
                ),
            )
        else:
            await self.use_case.reveal_token(
                username="owner",
                token_id=self.factory.core.hex_id(),
                password=Secret("incorrect"),
                now=self.now,
            )

    @pytest.mark.parametrize("operation", ["create", "reveal"])
    async def test_incorrect_confirmation_is_forbidden(self, operation: str) -> None:
        with pytest.raises(ApiTokenPasswordConfirmationError) as error:
            await self.confirm_password(operation=operation)
        assert str(error.value) == "Current-password confirmation failed"
        self.storage.create_token.assert_not_called()
        self.storage.get_token.assert_not_called()

    @pytest.mark.parametrize("operation", ["create", "reveal"])
    async def test_missing_account_remains_unauthorized(self, operation: str) -> None:
        self.storage.get_user.side_effect = UserNotFoundError
        with pytest.raises(UnauthorizedError):
            await self.confirm_password(operation=operation)
        self.hasher.verify_password.assert_not_called()

    @pytest.mark.parametrize("operation", ["create", "reveal"])
    async def test_inactive_account_remains_unauthorized(self, operation: str) -> None:
        self.storage.get_user.return_value = self.factory.core.user(
            username="owner", is_active=False
        )
        with pytest.raises(UnauthorizedError):
            await self.confirm_password(operation=operation)
        self.hasher.verify_password.assert_not_called()

    @pytest.mark.parametrize("status", ["expired", "revoked"])
    async def test_inactive_token_reveal_is_forbidden_but_authentication_is_unauthorized(
        self,
        status: str,
    ) -> None:
        self.hasher.verify_password.return_value = True, False
        token = ApiToken(
            id=self.factory.core.hex_id(),
            username="owner",
            name="CLI",
            permissions=frozenset({"auth.account.read"}),
            secret_hash="a" * 64,
            secret=Secret("test-token-secret"),
            created_at=self.now - timedelta(days=1),
            expires_at=self.now if status == "expired" else self.now + timedelta(hours=1),
            last_used_at=None,
            revoked_at=self.now if status == "revoked" else None,
        )
        self.storage.get_token.return_value = token
        self.storage.get_token_by_hash.return_value = token
        with pytest.raises(ApiTokenInactiveError):
            await self.confirm_password(operation="reveal")
        with pytest.raises(UnauthorizedError):
            await self.use_case.verify(secret=token.secret, now=self.now)
        self.storage.touch_token.assert_not_called()
