from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta

from core.account.avatar_schemas import (
    AccountAvatarUpload,
    AvatarOrphanCleanupResult,
    CurrentAccountAvatarContent,
    CurrentAccountAvatarMutationResult,
)
from core.account.clients import (
    AccountAvatarClient,
    AccountAvatarProcessor,
    AccountAvatarRollbackRegistrar,
)
from core.account.enums import ManagedAccountActionEnum
from core.account.exceptions import (
    AccountAvatarNotFoundError,
    AccountAvatarStorageError,
    AccountUsernameAlreadyExistsError,
    InvalidManagedAccountRoleError,
    ManagedAccountActionForbiddenError,
)
from core.account.schemas import (
    CurrentAccount,
    CurrentAccountUpdateParams,
    ManagedAccount,
    ManagedAccountCreateOperationParams,
    ManagedAccountFilters,
    ManagedAccountPasswordUpdateOperationParams,
    ManagedAccountRoleUpdateOperationParams,
    ManagedAccounts,
    ManagedAccountSession,
    ManagedAccountSessionRevocationResult,
    ManagedAccountSessionRevokeOperationParams,
    ManagedAccountSessions,
    ManagedAccountSessionsOperationParams,
    ManagedAccountSessionsRevokeOthersOperationParams,
    ManagedAccountTargetOperationParams,
)
from core.account.storages import CurrentAccountStorage, ManagedAccountStorage
from core.auth.enums import RoleEnum
from core.auth.exceptions import UserNotFoundError
from core.auth.password_hashers import PasswordHasher
from core.auth.storages import AuthSessionStorage
from core.generators import HexUuidIdGenerator


@dataclass(kw_only=True, slots=True, frozen=True)
class AvatarOrphanCleanupUseCase:
    storage: CurrentAccountStorage
    client: AccountAvatarClient
    retention_seconds: int = 24 * 60 * 60

    async def prune(self, *, current_datetime: datetime) -> AvatarOrphanCleanupResult:
        object_names = await self.client.list_objects_older_than(
            cutoff=current_datetime - timedelta(seconds=self.retention_seconds),
        )
        referenced_names = await self.storage.list_avatar_object_names()
        referenced_count = 0
        deleted_count = 0
        failed_count = 0
        for object_name in object_names:
            if object_name in referenced_names:
                referenced_count += 1
                continue
            try:
                await self.client.delete(object_name=object_name)
            except AccountAvatarStorageError:
                failed_count += 1
            else:
                deleted_count += 1
        return AvatarOrphanCleanupResult(
            scanned_count=len(object_names),
            referenced_count=referenced_count,
            deleted_count=deleted_count,
            failed_count=failed_count,
        )


@dataclass(kw_only=True, slots=True, frozen=True)
class CurrentAccountUseCase:
    storage: CurrentAccountStorage
    avatar_client: AccountAvatarClient
    avatar_processor: AccountAvatarProcessor
    id_generator: HexUuidIdGenerator

    async def get_account(self, *, username: str) -> CurrentAccount:
        return await self.storage.get_current_account(username=username)

    async def update_account(
        self,
        *,
        username: str,
        params: CurrentAccountUpdateParams,
    ) -> CurrentAccount:
        return await self.storage.update_current_account(
            username=username,
            params=params.normalized(),
        )

    async def replace_avatar(
        self,
        *,
        username: str,
        upload: AccountAvatarUpload,
        rollback_registrar: AccountAvatarRollbackRegistrar,
    ) -> CurrentAccountAvatarMutationResult:
        current = await self.storage.get_current_account(username=username)
        processed = self.avatar_processor.process(upload=upload)
        object_name = f"avatars/{self.id_generator.get_next()}.webp"
        await self.avatar_client.upload(
            object_name=object_name,
            content=processed.content,
        )
        rollback_registrar.register_new_object(object_name=object_name)
        updated = await self.storage.update_avatar_object_name(
            username=username,
            object_name=object_name,
        )
        return CurrentAccountAvatarMutationResult(
            account=updated,
            old_object_name=current.avatar_object_name,
        )

    async def remove_avatar(self, *, username: str) -> CurrentAccountAvatarMutationResult:
        current = await self.storage.get_current_account(username=username)
        if current.avatar_object_name is None:
            return CurrentAccountAvatarMutationResult(account=current, old_object_name=None)
        updated = await self.storage.update_avatar_object_name(
            username=username,
            object_name=None,
        )
        return CurrentAccountAvatarMutationResult(
            account=updated,
            old_object_name=current.avatar_object_name,
        )

    async def get_avatar(self, *, username: str) -> CurrentAccountAvatarContent:
        account = await self.storage.get_current_account(username=username)
        if account.avatar_object_name is None:
            raise AccountAvatarNotFoundError
        return CurrentAccountAvatarContent(
            content=self.avatar_client.stream(object_name=account.avatar_object_name),
        )


@dataclass(kw_only=True, slots=True, frozen=True)
class AccountsUseCase:
    storage: ManagedAccountStorage
    hasher: PasswordHasher
    auth_session_storage: AuthSessionStorage

    async def list_accounts(self, *, filters: ManagedAccountFilters) -> ManagedAccounts:
        accounts, total_count = await self.storage.list_managed_accounts(filters=filters)
        return ManagedAccounts.from_page(
            values=accounts,
            total_count=total_count,
            page_size=filters.page_size,
        )

    async def get_account(self, *, username: str) -> ManagedAccount:
        return await self.storage.get_managed_account(username=username)

    async def list_account_sessions(
        self,
        *,
        params: ManagedAccountSessionsOperationParams,
    ) -> ManagedAccountSessions:
        target_account = await self.storage.get_managed_account(username=params.target_username)
        current_account = await self.storage.get_managed_account(username=params.current_username)
        current_account.ensure_can_manage_account(
            target=target_account,
            action=ManagedAccountActionEnum.MANAGE_SESSIONS,
        )
        sessions = await self.auth_session_storage.list_user_sessions(
            username=params.target_username,
            active_at=params.current_datetime,
        )
        return ManagedAccountSessions(
            values=[
                ManagedAccountSession.from_auth_session(
                    session=session,
                    current_session_id=params.current_session_id,
                )
                for session in sessions
            ],
        )

    async def revoke_account_session(
        self,
        *,
        params: ManagedAccountSessionRevokeOperationParams,
    ) -> ManagedAccountSessionRevocationResult:
        target_account = await self.storage.get_managed_account(username=params.target_username)
        current_account = await self.storage.get_managed_account(username=params.current_username)
        current_account.ensure_can_manage_account(
            target=target_account,
            action=ManagedAccountActionEnum.MANAGE_SESSIONS,
        )
        await self.auth_session_storage.revoke_user_session(
            username=params.target_username,
            session_id=params.target_session_id,
        )
        return ManagedAccountSessionRevocationResult(
            current_session_revoked=params.target_session_id == params.current_session_id,
        )

    async def revoke_all_account_sessions(
        self,
        *,
        params: ManagedAccountSessionsOperationParams,
    ) -> ManagedAccountSessionRevocationResult:
        target_account = await self.storage.get_managed_account(username=params.target_username)
        current_account = await self.storage.get_managed_account(username=params.current_username)
        current_account.ensure_can_manage_account(
            target=target_account,
            action=ManagedAccountActionEnum.MANAGE_SESSIONS,
        )
        await self.auth_session_storage.revoke_user_sessions(username=params.target_username)
        return ManagedAccountSessionRevocationResult(
            current_session_revoked=(
                params.target_username.casefold() == params.current_username.casefold()
            ),
        )

    async def revoke_other_account_sessions(
        self,
        *,
        params: ManagedAccountSessionsRevokeOthersOperationParams,
    ) -> ManagedAccountSessionRevocationResult:
        target_account = await self.storage.get_managed_account(username=params.target_username)
        current_account = await self.storage.get_managed_account(username=params.current_username)
        current_account.ensure_can_manage_account(
            target=target_account,
            action=ManagedAccountActionEnum.MANAGE_SESSIONS,
        )
        if params.target_username.casefold() != params.current_username.casefold():
            raise ManagedAccountActionForbiddenError
        await self.auth_session_storage.revoke_user_sessions_except(
            username=params.target_username,
            except_session_id=params.current_session_id,
        )
        return ManagedAccountSessionRevocationResult(current_session_revoked=False)

    async def create_account(
        self,
        *,
        params: ManagedAccountCreateOperationParams,
    ) -> ManagedAccount:
        create_params = params.create_params
        if create_params.role not in {RoleEnum.ADMIN, RoleEnum.MODERATOR}:
            raise InvalidManagedAccountRoleError
        current_account = await self.storage.get_managed_account(username=params.current_username)
        current_account.ensure_can_create_account_with_role(role=create_params.role)
        with suppress(UserNotFoundError):
            await self.storage.get_user_by_username(username=create_params.username)
            raise AccountUsernameAlreadyExistsError
        return await self.storage.create_managed_account(
            username=create_params.username,
            role=create_params.role,
            password_hash=self.hasher.hash_password(create_params.password.get_secret_value()),
            is_active=create_params.is_active,
        )

    async def update_role(
        self,
        *,
        params: ManagedAccountRoleUpdateOperationParams,
    ) -> ManagedAccount:
        role_params = params.role_params
        if role_params.role not in {RoleEnum.ADMIN, RoleEnum.MODERATOR}:
            raise InvalidManagedAccountRoleError
        target_account = await self.storage.get_managed_account(username=params.target_username)
        current_account = await self.storage.get_managed_account(username=params.current_username)
        current_account.ensure_can_update_account_role(target=target_account, role=role_params.role)
        return await self.storage.update_managed_account_role(
            username=params.target_username,
            role=role_params.role,
        )

    async def update_password(
        self,
        *,
        params: ManagedAccountPasswordUpdateOperationParams,
    ) -> ManagedAccount:
        password_params = params.password_params
        target_account = await self.storage.get_managed_account(username=params.target_username)
        current_account = await self.storage.get_managed_account(username=params.current_username)
        current_account.ensure_can_manage_account(
            target=target_account,
            action=ManagedAccountActionEnum.UPDATE_PASSWORD,
        )
        account = await self.storage.update_managed_account_password(
            username=params.target_username,
            password_hash=self.hasher.hash_password(password_params.password.get_secret_value()),
        )
        await self.auth_session_storage.revoke_user_sessions(username=params.target_username)
        return account

    async def activate_account(
        self,
        *,
        params: ManagedAccountTargetOperationParams,
    ) -> ManagedAccount:
        target_account = await self.storage.get_managed_account(username=params.target_username)
        current_account = await self.storage.get_managed_account(username=params.current_username)
        current_account.ensure_can_manage_account(
            target=target_account,
            action=ManagedAccountActionEnum.ACTIVATE,
        )
        return await self.storage.activate_managed_account(username=params.target_username)

    async def deactivate_account(
        self,
        *,
        params: ManagedAccountTargetOperationParams,
    ) -> ManagedAccount:
        target_account = await self.storage.get_managed_account(username=params.target_username)
        current_account = await self.storage.get_managed_account(username=params.current_username)
        current_account.ensure_can_manage_account(
            target=target_account,
            action=ManagedAccountActionEnum.DEACTIVATE,
        )
        account = await self.storage.deactivate_managed_account(username=params.target_username)
        await self.auth_session_storage.revoke_user_sessions(username=params.target_username)
        return account

    async def delete_account(self, *, params: ManagedAccountTargetOperationParams) -> None:
        target_account = await self.storage.get_managed_account(username=params.target_username)
        current_account = await self.storage.get_managed_account(username=params.current_username)
        current_account.ensure_can_manage_account(
            target=target_account,
            action=ManagedAccountActionEnum.DELETE,
        )
        await self.storage.delete_managed_account(username=params.target_username)
        await self.auth_session_storage.revoke_user_sessions(username=params.target_username)
