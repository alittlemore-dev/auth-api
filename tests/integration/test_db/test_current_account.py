# ruff: noqa: S106
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.account.enums import AccountLanguageEnum, AccountThemeEnum, GenderEnum
from core.account.schemas import AccountSettings, CurrentAccount, CurrentAccountUpdateParams
from core.auth.enums import RoleEnum
from core.auth.exceptions import UserNotFoundError
from core.schemas import Secret
from infra.postgresql.storages.users import UserAccountDatabaseStorage
from tests.test_cases import StorageTestCase


class TestCurrentAccountStorage(StorageTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, session: AsyncSession) -> None:
        self.storage = UserAccountDatabaseStorage(session=session)
        await self.storage_helper.create_user(
            self.factory.core.user(
                username="profile-user",
                password_hash="password",
                role=RoleEnum.USER,
            ),
        )

    async def test_profile_values_are_encrypted_at_rest_and_returned_as_secrets(self) -> None:
        account = await self.storage.update_current_account(
            username="PROFILE-USER",
            params=CurrentAccountUpdateParams(
                first_name=Secret("Dmitriy"),
                last_name=Secret("Lunev"),
                middle_name=Secret("Sergeevich"),
                gender=Secret(GenderEnum.MALE),
            ),
        )

        assert account == CurrentAccount(
            username="profile-user",
            role=RoleEnum.USER,
            first_name=Secret("Dmitriy"),
            last_name=Secret("Lunev"),
            middle_name=Secret("Sergeevich"),
            gender=Secret(GenderEnum.MALE),
            avatar_object_name=None,
        )
        raw_row = (
            (
                await self.db_session.execute(
                    text(
                        "SELECT first_name, last_name, middle_name, gender "
                        "FROM auth__user_model WHERE username = :username",
                    ),
                    {"username": "profile-user"},
                )
            )
            .mappings()
            .one()
        )
        assert raw_row["first_name"] != "Dmitriy"
        assert raw_row["last_name"] != "Lunev"
        assert raw_row["middle_name"] != "Sergeevich"
        assert raw_row["gender"] != "male"
        assert all(str(value).startswith("gAAAA") for value in raw_row.values())

    async def test_update_changes_only_selected_fields_and_allows_explicit_null(self) -> None:
        await self.storage.update_current_account(
            username="profile-user",
            params=CurrentAccountUpdateParams(
                first_name=Secret("Dmitriy"),
                last_name=Secret("Lunev"),
                middle_name=Secret("Sergeevich"),
                gender=Secret(GenderEnum.MALE),
            ),
        )

        account = await self.storage.update_current_account(
            username="profile-user",
            params=CurrentAccountUpdateParams(
                first_name=Secret("Dima"),
                middle_name=None,
            ),
        )

        assert account.first_name == Secret("Dima")
        assert account.last_name == Secret("Lunev")
        assert account.middle_name is None
        assert account.gender == Secret(GenderEnum.MALE)

    async def test_avatar_reference_operations_do_not_expose_profile_data(self) -> None:
        updated = await self.storage.update_avatar_object_name(
            username="profile-user",
            object_name="avatars/random.webp",
        )

        assert updated.avatar_object_name == "avatars/random.webp"
        assert await self.storage.list_avatar_object_names() == frozenset(
            {"avatars/random.webp"},
        )

        cleared = await self.storage.update_avatar_object_name(
            username="profile-user",
            object_name=None,
        )

        assert cleared.avatar_object_name is None
        assert await self.storage.list_avatar_object_names() == frozenset()

    async def test_current_account_lookup_is_case_insensitive(self) -> None:
        account = await self.storage.get_current_account(username="PROFILE-USER")

        assert account.username == "profile-user"
        assert account.role is RoleEnum.USER

    async def test_missing_current_account_get_raises_user_not_found(self) -> None:
        with pytest.raises(UserNotFoundError):
            await self.storage.get_current_account(username="missing")

    async def test_missing_current_account_update_raises_user_not_found(self) -> None:
        with pytest.raises(UserNotFoundError):
            await self.storage.update_current_account(
                username="missing",
                params=CurrentAccountUpdateParams(
                    first_name=Secret("Missing"),
                ),
            )

    async def test_missing_current_account_avatar_update_raises_user_not_found(self) -> None:
        with pytest.raises(UserNotFoundError):
            await self.storage.update_avatar_object_name(
                username="missing",
                object_name="avatars/random.webp",
            )

    async def test_settings_round_trip_preserves_profile_and_other_accounts(self) -> None:
        await self.storage_helper.create_user(self.factory.core.user(username="other-user"))
        await self.storage.update_current_account(
            username="profile-user",
            params=CurrentAccountUpdateParams(first_name=Secret("Name")),
        )
        settings = AccountSettings(language=AccountLanguageEnum.RU, theme=AccountThemeEnum.DARK)
        result = await self.storage.update_settings(username="profile-user", settings=settings)
        assert result.settings == settings
        assert result.first_name == Secret("Name")
        self.storage.session.expire_all()
        loaded = await self.storage.get_current_account(username="profile-user")
        assert loaded.settings == settings
        other = await self.storage.get_current_account(username="other-user")
        assert other.settings == AccountSettings()
        avatar = await self.storage.update_avatar_object_name(
            username="profile-user", object_name="avatar.webp"
        )
        assert avatar.settings == settings
