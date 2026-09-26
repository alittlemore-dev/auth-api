# ruff: noqa: S106
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.account.enums import AccountLanguageEnum, AccountThemeEnum, TelegramBotId
from core.account.schemas import AccountSettings, TelegramBotSettings
from core.auth.enums import RoleEnum
from infra.postgresql.models import UserModel
from infra.postgresql.storages.users import UserAccountDatabaseStorage
from tests.test_cases import StorageTestCase


class TestAccountSettingsStorage(StorageTestCase):
    async def test_replaces_all_settings_including_telegram_bots(
        self,
        session: AsyncSession,
    ) -> None:
        await self.storage_helper.create_user(
            self.factory.core.user(
                username="anna",
                password_hash="password",
                role=RoleEnum.USER,
            ),
        )
        account_storage = UserAccountDatabaseStorage(session=session)
        await account_storage.update_settings(
            username="anna",
            settings=AccountSettings(
                language=AccountLanguageEnum.RU,
                theme=AccountThemeEnum.DARK,
                telegram_bots={
                    TelegramBotId.PERSONAL_WORKSPACE: TelegramBotSettings(enabled=True, notify=True)
                },
            ),
        )
        session.expire_all()

        user = await session.scalar(select(UserModel).where(UserModel.username == "anna"))
        assert user is not None
        assert user.settings.telegram_bots[TelegramBotId.PERSONAL_WORKSPACE].enabled
        assert user.settings.telegram_bots[TelegramBotId.PERSONAL_WORKSPACE].notify
        assert user.settings.language == AccountLanguageEnum.RU
        assert user.settings.theme == AccountThemeEnum.DARK
        await account_storage.update_settings(username="anna", settings=AccountSettings())
        session.expire_all()
        account = await account_storage.get_current_account(username="anna")
        assert account.settings == AccountSettings()
