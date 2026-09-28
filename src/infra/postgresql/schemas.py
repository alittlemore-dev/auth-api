from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from core.account.enums import AccountLanguageEnum, AccountThemeEnum, TelegramBotId
from core.account.schemas import AccountSettings, TelegramBotSettings
from infra.config.constants import constants
from infra.config.validators import validate_time_zone_identifier

AccountTimeZone = Annotated[ZoneInfo, BeforeValidator(validate_time_zone_identifier)]


class TelegramBotSettingsSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    notify: bool = False


class AccountSettingsSchema(BaseModel):
    model_config = ConfigDict(validate_default=True, frozen=True)

    language: AccountLanguageEnum = AccountLanguageEnum.EN
    theme: AccountThemeEnum = AccountThemeEnum.LIGHT
    time_zone: AccountTimeZone = constants.account_time_zone.default
    telegram_bots: dict[TelegramBotId, TelegramBotSettingsSchema] = Field(default_factory=dict)

    def to_domain_schema(self) -> AccountSettings:
        return AccountSettings(
            language=self.language,
            theme=self.theme,
            time_zone=self.time_zone,
            telegram_bots={
                bot_id: TelegramBotSettings(enabled=value.enabled, notify=value.notify)
                for bot_id, value in self.telegram_bots.items()
            },
        )

    @classmethod
    def from_domain_schema(cls, schema: AccountSettings) -> AccountSettingsSchema:
        return cls(
            language=schema.language,
            theme=schema.theme,
            time_zone=schema.time_zone,
            telegram_bots={
                bot_id: TelegramBotSettingsSchema(enabled=value.enabled, notify=value.notify)
                for bot_id, value in schema.telegram_bots.items()
            },
        )
