from pydantic import BaseModel, ConfigDict

from core.account.enums import AccountLanguageEnum, AccountThemeEnum
from core.account.schemas import AccountSettings


class AccountSettingsSchema(BaseModel):
    model_config = ConfigDict(validate_default=True, frozen=True)

    language: AccountLanguageEnum = AccountLanguageEnum.EN
    theme: AccountThemeEnum = AccountThemeEnum.LIGHT

    def to_domain_schema(self) -> AccountSettings:
        return AccountSettings(language=self.language, theme=self.theme)

    @classmethod
    def from_domain_schema(cls, schema: AccountSettings) -> AccountSettingsSchema:
        return cls(language=schema.language, theme=schema.theme)
