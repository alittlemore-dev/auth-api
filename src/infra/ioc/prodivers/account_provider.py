from collections.abc import AsyncIterator
from typing import cast

from aiobotocore.config import AioConfig
from aiobotocore.session import get_session
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession
from types_aiobotocore_s3.client import S3Client

from core.account.clients import (
    AccountAvatarClient,
    AccountAvatarProcessor,
    AccountAvatarRollbackRegistrar,
)
from core.account.storages import CurrentAccountStorage, ManagedAccountStorage, UserAccountStorage
from core.account.use_cases import (
    AccountsUseCase,
    AvatarOrphanCleanupUseCase,
    CurrentAccountUseCase,
)
from core.auth.password_hashers import PasswordHasher
from core.auth.storages import AuthSessionStorage
from core.generators import HexUuidIdGenerator
from infra.account_avatar_actions import RequestAccountAvatarRollbackRegistrar
from infra.config.constants import constants
from infra.config.settings import settings
from infra.files.account_avatar_processor import PillowAccountAvatarProcessor
from infra.post_commit_actions import RollbackActions
from infra.postgresql.storages.users import UserAccountDatabaseStorage
from infra.s3.account_avatar_client import S3AccountAvatarClient


class UserAccountProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_s3_client(self) -> AsyncIterator[S3Client]:
        config = AioConfig(
            signature_version="s3v4",
            s3={"addressing_style": settings.minio.addressing_style},
        )
        session = get_session()
        async with session.create_client(
            "s3",
            endpoint_url=settings.minio.endpoint_url,
            region_name=settings.minio.region,
            aws_access_key_id=settings.minio.access_key,
            aws_secret_access_key=settings.minio.secret_key.get_secret_value(),
            config=config,
        ) as client:
            yield cast("S3Client", client)

    @provide(scope=Scope.APP)
    async def provide_account_avatar_client(self, client: S3Client) -> AccountAvatarClient:
        return S3AccountAvatarClient(
            client=client,
            bucket_name=settings.minio.bucket,
            stream_chunk_size=constants.account_avatar.stream_chunk_size,
        )

    @provide(scope=Scope.APP)
    async def provide_account_avatar_processor(self) -> AccountAvatarProcessor:
        return PillowAccountAvatarProcessor()

    @provide(scope=Scope.REQUEST)
    async def provide_avatar_orphan_cleanup_use_case(
        self,
        storage: CurrentAccountStorage,
        avatar_client: AccountAvatarClient,
    ) -> AvatarOrphanCleanupUseCase:
        return AvatarOrphanCleanupUseCase(
            storage=storage,
            client=avatar_client,
            retention_seconds=constants.account_avatar.orphan_retention_seconds,
        )

    @provide(scope=Scope.REQUEST)
    async def provide_user_storage(self, session: AsyncSession) -> UserAccountStorage:
        return UserAccountDatabaseStorage(session=session)

    @provide(scope=Scope.REQUEST)
    async def provide_managed_account_storage(
        self,
        session: AsyncSession,
    ) -> ManagedAccountStorage:
        return UserAccountDatabaseStorage(session=session)

    @provide(scope=Scope.REQUEST)
    async def provide_current_account_storage(
        self,
        session: AsyncSession,
    ) -> CurrentAccountStorage:
        return UserAccountDatabaseStorage(session=session)

    @provide(scope=Scope.REQUEST)
    async def provide_current_account_use_case(
        self,
        storage: CurrentAccountStorage,
        avatar_client: AccountAvatarClient,
        avatar_processor: AccountAvatarProcessor,
        id_generator: HexUuidIdGenerator,
    ) -> CurrentAccountUseCase:
        return CurrentAccountUseCase(
            storage=storage,
            avatar_client=avatar_client,
            avatar_processor=avatar_processor,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    async def provide_account_avatar_rollback_registrar(
        self,
        avatar_client: AccountAvatarClient,
        rollback_actions: RollbackActions,
    ) -> AccountAvatarRollbackRegistrar:
        return RequestAccountAvatarRollbackRegistrar(
            client=avatar_client,
            rollback_actions=rollback_actions,
        )

    @provide(scope=Scope.REQUEST)
    async def provide_accounts_use_case(
        self,
        storage: ManagedAccountStorage,
        hasher: PasswordHasher,
        auth_session_storage: AuthSessionStorage,
    ) -> AccountsUseCase:
        return AccountsUseCase(
            storage=storage,
            hasher=hasher,
            auth_session_storage=auth_session_storage,
        )
