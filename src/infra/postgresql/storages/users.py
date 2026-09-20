from dataclasses import dataclass

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.account.exceptions import ManagedAccountNotFoundError
from core.account.schemas import (
    AccountSettings,
    CurrentAccount,
    CurrentAccountUpdateParams,
    ManagedAccount,
    ManagedAccountFilters,
)
from core.account.storages import CurrentAccountStorage, ManagedAccountStorage
from core.auth.enums import RoleEnum
from core.auth.exceptions import UserNotFoundError
from core.auth.schemas import User
from core.schemas import UNSET
from infra.postgresql.models import UserModel
from infra.postgresql.schemas import AccountSettingsSchema

MANAGED_ACCOUNT_ROLES = (RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MODERATOR)


@dataclass(kw_only=True)
class UserAccountDatabaseStorage(ManagedAccountStorage, CurrentAccountStorage):
    session: AsyncSession

    async def get_user_by_username(self, username: str) -> User:
        stmt = select(UserModel).where(func.lower(UserModel.username) == username.lower())
        user = await self.session.scalar(stmt)
        if user is None:
            raise UserNotFoundError
        return user.to_domain_schema()

    async def get_current_account(self, *, username: str) -> CurrentAccount:
        statement = select(UserModel).where(func.lower(UserModel.username) == username.lower())
        model = await self.session.scalar(statement)
        if model is None:
            raise UserNotFoundError
        return model.to_current_account_schema()

    async def update_current_account(
        self,
        *,
        username: str,
        params: CurrentAccountUpdateParams,
    ) -> CurrentAccount:
        values: dict[str, object] = {}
        if params.first_name is not UNSET:
            values["first_name"] = params.first_name
        if params.last_name is not UNSET:
            values["last_name"] = params.last_name
        if params.middle_name is not UNSET:
            values["middle_name"] = params.middle_name
        if params.gender is not UNSET:
            values["gender"] = params.gender
        statement = (
            update(UserModel)
            .where(func.lower(UserModel.username) == username.lower())
            .values(**values)
            .returning(UserModel)
        )
        model = await self.session.scalar(statement)
        if model is None:
            raise UserNotFoundError
        return model.to_current_account_schema()

    async def update_settings(self, *, username: str, settings: AccountSettings) -> CurrentAccount:
        statement = (
            update(UserModel)
            .where(func.lower(UserModel.username) == username.lower())
            .values(settings=AccountSettingsSchema.from_domain_schema(settings))
            .returning(UserModel)
        )
        model = await self.session.scalar(statement)
        if model is None:
            raise UserNotFoundError
        return model.to_current_account_schema()

    async def update_avatar_object_name(
        self,
        *,
        username: str,
        object_name: str | None,
    ) -> CurrentAccount:
        statement = (
            update(UserModel)
            .where(func.lower(UserModel.username) == username.lower())
            .values(avatar_object_name=object_name)
            .returning(UserModel)
        )
        model = await self.session.scalar(statement)
        if model is None:
            raise UserNotFoundError
        return model.to_current_account_schema()

    async def list_avatar_object_names(self) -> frozenset[str]:
        statement = select(UserModel.avatar_object_name).where(
            UserModel.avatar_object_name.is_not(None),
        )
        object_names = await self.session.scalars(statement)
        return frozenset(object_name for object_name in object_names if object_name is not None)

    async def list_managed_accounts(
        self,
        *,
        filters: ManagedAccountFilters,
    ) -> tuple[list[ManagedAccount], int]:
        query = (
            select(UserModel)
            .where(UserModel.role.in_(MANAGED_ACCOUNT_ROLES))
            .order_by(func.lower(UserModel.username), UserModel.username)
            .offset(filters.offset)
            .limit(filters.limit)
        )
        count_query = select(func.count(UserModel.username)).where(
            UserModel.role.in_(MANAGED_ACCOUNT_ROLES),
        )
        models = await self.session.scalars(query)
        total_count = (await self.session.scalar(count_query)) or 0
        return [model.to_managed_account_schema() for model in models], total_count

    async def get_managed_account(self, *, username: str) -> ManagedAccount:
        query = select(UserModel).where(
            func.lower(UserModel.username) == username.lower(),
            UserModel.role.in_(MANAGED_ACCOUNT_ROLES),
        )
        model = await self.session.scalar(query)
        if model is None:
            raise ManagedAccountNotFoundError
        return model.to_managed_account_schema()

    async def create_managed_account(
        self,
        *,
        username: str,
        role: RoleEnum,
        password_hash: str,
        is_active: bool,
    ) -> ManagedAccount:
        statement = (
            insert(UserModel)
            .values(
                username=username,
                role=role,
                password_hash=password_hash,
                is_active=is_active,
            )
            .returning(UserModel)
        )
        model = await self.session.scalar(statement)
        if model is None:
            raise ManagedAccountNotFoundError
        return model.to_managed_account_schema()

    async def update_managed_account_role(
        self,
        *,
        username: str,
        role: RoleEnum,
    ) -> ManagedAccount:
        statement = (
            update(UserModel)
            .where(
                func.lower(UserModel.username) == username.lower(),
                UserModel.role.in_(MANAGED_ACCOUNT_ROLES),
            )
            .values(role=role)
            .returning(UserModel)
        )
        model = await self.session.scalar(statement)
        if model is None:
            raise ManagedAccountNotFoundError
        return model.to_managed_account_schema()

    async def update_managed_account_password(
        self,
        *,
        username: str,
        password_hash: str,
    ) -> ManagedAccount:
        statement = (
            update(UserModel)
            .where(
                func.lower(UserModel.username) == username.lower(),
                UserModel.role.in_(MANAGED_ACCOUNT_ROLES),
            )
            .values(password_hash=password_hash)
            .returning(UserModel)
        )
        model = await self.session.scalar(statement)
        if model is None:
            raise ManagedAccountNotFoundError
        return model.to_managed_account_schema()

    async def activate_managed_account(self, *, username: str) -> ManagedAccount:
        statement = (
            update(UserModel)
            .where(
                func.lower(UserModel.username) == username.lower(),
                UserModel.role.in_(MANAGED_ACCOUNT_ROLES),
            )
            .values(is_active=True)
            .returning(UserModel)
        )
        model = await self.session.scalar(statement)
        if model is None:
            raise ManagedAccountNotFoundError
        return model.to_managed_account_schema()

    async def deactivate_managed_account(self, *, username: str) -> ManagedAccount:
        statement = (
            update(UserModel)
            .where(
                func.lower(UserModel.username) == username.lower(),
                UserModel.role.in_(MANAGED_ACCOUNT_ROLES),
            )
            .values(is_active=False)
            .returning(UserModel)
        )
        model = await self.session.scalar(statement)
        if model is None:
            raise ManagedAccountNotFoundError
        return model.to_managed_account_schema()

    async def delete_managed_account(self, *, username: str) -> None:
        statement = (
            delete(UserModel)
            .where(
                func.lower(UserModel.username) == username.lower(),
                UserModel.role.in_(MANAGED_ACCOUNT_ROLES),
            )
            .returning(UserModel.username)
        )
        deleted_username = await self.session.scalar(statement)
        if deleted_username is None:
            raise ManagedAccountNotFoundError
