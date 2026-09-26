from typing import Annotated

from litestar.datastructures.upload_file import UploadFile
from pydantic import ConfigDict, Field, field_validator

from core.account.avatar_schemas import AccountAvatarUpload
from core.account.enums import AccountLanguageEnum, AccountThemeEnum, GenderEnum, TelegramBotId
from core.account.exceptions import InvalidAccountAvatarError
from core.account.schemas import (
    AccountSettings,
    CurrentAccount,
    CurrentAccountUpdateParams,
    TelegramBotSettings,
)
from core.auth.enums import RoleEnum
from core.schemas import UNSET, Secret, UnsetType
from entrypoints.litestar.api.schemas import CamelCaseSchema
from infra.config.constants import constants


class AccountAvatarUploadRequestSchema(CamelCaseSchema):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file: Annotated[UploadFile, Field(title="Avatar image")]

    async def to_domain_schema(self) -> AccountAvatarUpload:
        content = await self.file.read(constants.account_avatar.max_source_bytes + 1)
        if len(content) > constants.account_avatar.max_source_bytes:
            raise InvalidAccountAvatarError
        return AccountAvatarUpload(
            content=content,
            declared_mime_type=self.file.content_type or "application/octet-stream",
        )


class CurrentAccountUpdateRequestSchema(CamelCaseSchema):
    first_name: Annotated[str | None, Field(max_length=100)] = None
    last_name: Annotated[str | None, Field(max_length=100)] = None
    middle_name: Annotated[str | None, Field(max_length=100)] = None
    gender: GenderEnum | None = None

    @field_validator("first_name", "last_name", "middle_name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    def to_domain_schema(self) -> CurrentAccountUpdateParams:
        return CurrentAccountUpdateParams(
            first_name=self._to_patch_value("first_name", self.first_name),
            last_name=self._to_patch_value("last_name", self.last_name),
            middle_name=self._to_patch_value("middle_name", self.middle_name),
            gender=self._to_patch_value("gender", self.gender),
        )

    def _to_patch_value[T](
        self,
        field_name: str,
        value: T | None,
    ) -> Secret[T] | UnsetType | None:
        if field_name not in self.model_fields_set:
            return UNSET
        return Secret(value) if value is not None else None


class TelegramBotSettingsSchema(CamelCaseSchema):
    enabled: bool = False


class AccountSettingsSchema(CamelCaseSchema):
    model_config = ConfigDict(validate_default=True)

    language: AccountLanguageEnum = AccountLanguageEnum.EN
    theme: AccountThemeEnum = AccountThemeEnum.LIGHT
    telegram_bots: dict[TelegramBotId, TelegramBotSettingsSchema] = Field(default_factory=dict)

    def to_domain_schema(self) -> AccountSettings:
        return AccountSettings(
            language=self.language,
            theme=self.theme,
            telegram_bots={
                bot_id: TelegramBotSettings(enabled=value.enabled)
                for bot_id, value in self.telegram_bots.items()
            },
        )

    @classmethod
    def from_domain_schema(cls, schema: AccountSettings) -> AccountSettingsSchema:
        return cls(
            language=schema.language,
            theme=schema.theme,
            telegram_bots={
                bot_id: TelegramBotSettingsSchema(enabled=value.enabled)
                for bot_id, value in schema.telegram_bots.items()
            },
        )


class CurrentAccountResponseSchema(CamelCaseSchema):
    username: str
    role: RoleEnum
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    gender: GenderEnum | None
    settings: AccountSettingsSchema
    has_avatar: bool

    @classmethod
    def from_domain_schema(
        cls,
        *,
        schema: CurrentAccount,
    ) -> CurrentAccountResponseSchema:
        return cls.model_construct(
            settings=AccountSettingsSchema.from_domain_schema(schema.settings),
            username=schema.username,
            role=schema.role,
            first_name=(schema.first_name.get_secret_value() if schema.first_name else None),
            last_name=(schema.last_name.get_secret_value() if schema.last_name else None),
            middle_name=(schema.middle_name.get_secret_value() if schema.middle_name else None),
            gender=schema.gender.get_secret_value() if schema.gender else None,
            has_avatar=schema.avatar_object_name is not None,
        )
