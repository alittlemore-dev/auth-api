import hashlib
from typing import Any

from core.account.enums import GenderEnum
from core.account.schemas import CurrentAccount, ManagedAccount, ManagedAccounts
from core.auth.enums import RoleEnum
from core.auth.schemas import JwtUser, User
from core.auth.types import Token
from core.schemas import Secret
from core.types import SearchName


class CoreFactoryHelper:
    @classmethod
    def hex_id(cls, value: int | str = 1) -> str:
        if isinstance(value, str):
            return value
        return f"{value % (1 << 128):032x}"

    @classmethod
    def hex_id_from_text(cls, value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()[:32]

    @classmethod
    def user(
        cls,
        username: str = "",
        password_hash: str = "",
        role: RoleEnum = RoleEnum.USER,
        is_active: bool = True,
    ) -> User:
        return User(
            username=username,
            password_hash=Secret(password_hash),
            role=role,
            is_active=is_active,
        )

    @classmethod
    def managed_accounts(
        cls,
        values: list[ManagedAccount] | None = None,
        total_count: int = 0,
        total_pages: int = 0,
    ) -> ManagedAccounts:
        return ManagedAccounts(
            values=values or [],
            total_count=total_count,
            total_pages=total_pages,
        )

    @classmethod
    def current_account(
        cls,
        username: str = "test",
        role: RoleEnum = RoleEnum.USER,
        first_name: str | None = None,
        last_name: str | None = None,
        middle_name: str | None = None,
        gender: GenderEnum | None = None,
        avatar_object_name: str | None = None,
    ) -> CurrentAccount:
        return CurrentAccount(
            username=username,
            role=role,
            first_name=Secret(first_name) if first_name is not None else None,
            last_name=Secret(last_name) if last_name is not None else None,
            middle_name=Secret(middle_name) if middle_name is not None else None,
            gender=Secret(gender) if gender is not None else None,
            avatar_object_name=avatar_object_name,
        )

    @classmethod
    def jwt_user(
        cls,
        username: str = "test",
        role: RoleEnum = RoleEnum.ADMIN,
    ) -> JwtUser:
        return JwtUser(username=username, role=role)

    @classmethod
    def token(cls, value: bytes) -> Token:
        return Token(value)

    @classmethod
    def search_name(cls, value: Any) -> SearchName:
        return SearchName(value)
