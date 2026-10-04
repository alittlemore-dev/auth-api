import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from argon2 import PasswordHasher as Argon2
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.account.schemas import (
    ManagedAccountPasswordUpdateOperationParams,
    ManagedAccountPasswordUpdateParams,
)
from core.account.use_cases import AccountsUseCase
from core.api_tokens.exceptions import ApiTokenPasswordConfirmationError
from core.api_tokens.generators import ApiTokenSecretGenerator
from core.api_tokens.schemas import ApiTokenCreate
from core.api_tokens.services import ApiPermissionRegistry
from core.api_tokens.use_cases import ApiTokensUseCase
from core.auth.enums import RoleEnum
from core.auth.exceptions import UnauthorizedError
from core.auth.storages import AuthSessionStorage
from core.schemas import Secret
from infra.auth.password_hashers import Argon2PasswordHasher
from infra.postgresql.models import UserModel
from infra.postgresql.storages.api_tokens import ApiTokenDatabaseStorage
from infra.postgresql.storages.users import UserAccountDatabaseStorage


async def test_password_update_and_token_creation_serialize_on_account(
    session: AsyncSession,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    hasher = Argon2PasswordHasher(context=Argon2())
    session.add(
        UserModel(
            username="owner",
            password_hash=hasher.hash_password("old-password"),
            role=RoleEnum.OWNER,
            is_active=True,
        )
    )
    await session.commit()
    now = datetime.now(tz=UTC)
    params = ApiTokenCreate(
        name="concurrent",
        permissions=frozenset({"auth.account.read"}),
        expires_at=now + timedelta(hours=1),
    )
    async with session_maker() as creation_session, session_maker() as password_session:
        creation_storage = ApiTokenDatabaseStorage(session=creation_session)
        creating = ApiTokensUseCase(
            storage=creation_storage,
            hasher=hasher,
            generator=ApiTokenSecretGenerator(),
            registry=ApiPermissionRegistry(),
        )
        token = await creating.create_token(
            username="owner", password=Secret("old-password"), params=params, now=now
        )
        changing = AccountsUseCase(
            storage=UserAccountDatabaseStorage(session=password_session),
            hasher=hasher,
            auth_session_storage=Mock(spec=AuthSessionStorage),
            api_token_storage=ApiTokenDatabaseStorage(session=password_session),
        )
        password_update = asyncio.create_task(
            changing.update_password(
                params=ManagedAccountPasswordUpdateOperationParams(
                    target_username="owner",
                    current_username="owner",
                    password_params=ManagedAccountPasswordUpdateParams(
                        password=Secret("new-password")
                    ),
                ),
                current_datetime=now,
            )
        )
        # The pending account UPDATE must wait for issuance's account lock.
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(password_update), timeout=0.2)
        await creation_session.commit()
        await asyncio.wait_for(password_update, timeout=5)
        await password_session.commit()
    async with session_maker() as verifying_session:
        verifying = ApiTokensUseCase(
            storage=ApiTokenDatabaseStorage(session=verifying_session),
            hasher=hasher,
            generator=ApiTokenSecretGenerator(),
            registry=ApiPermissionRegistry(),
        )
        with pytest.raises(UnauthorizedError):
            await verifying.verify(secret=token.secret, now=now)
        with pytest.raises(ApiTokenPasswordConfirmationError):
            await verifying.create_token(
                username="owner", password=Secret("old-password"), params=params, now=now
            )
