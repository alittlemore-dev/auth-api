from typing import Annotated
from zoneinfo import ZoneInfo

from litestar.datastructures.upload_file import UploadFile
from pydantic import BeforeValidator, ConfigDict, Field, field_validator

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
from infra.config.validators import validate_time_zone_identifier

AccountTimeZone = Annotated[ZoneInfo, BeforeValidator(validate_time_zone_identifier)]


class AccountAvatarUploadRequestSchema(CamelCaseSchema):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file: Annotated[
        UploadFile,
        Field(
            title="Avatar image",
            description=(
                "Binary JPEG, PNG or WebP image; stored and served as WebP. Multipart "
                "body limit: 5 MiB."
            ),
        ),
    ]

    async def to_domain_schema(self) -> AccountAvatarUpload:
        content = await self.file.read(constants.account_avatar.max_source_bytes + 1)
        if len(content) > constants.account_avatar.max_source_bytes:
            raise InvalidAccountAvatarError
        return AccountAvatarUpload(
            content=content,
            declared_mime_type=self.file.content_type or "application/octet-stream",
        )


class CurrentAccountUpdateRequestSchema(CamelCaseSchema):
    first_name: Annotated[
        str | None,
        Field(
            max_length=100,
            description="Given name. Omit to preserve; null or blank clears it.",
            examples=["Dmitriy"],
        ),
    ] = None
    last_name: Annotated[
        str | None,
        Field(
            max_length=100,
            description="Family name. Omit to preserve; null or blank clears it.",
            examples=["Lunev"],
        ),
    ] = None
    middle_name: Annotated[
        str | None,
        Field(
            max_length=100,
            description="Middle name. Omit to preserve; null or blank clears it.",
            examples=["Alexandrovich"],
        ),
    ] = None
    gender: GenderEnum | None = Field(
        default=None,
        description="Profile gender. Omit to preserve; null clears it.",
        examples=["male"],
    )

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
    enabled: bool = Field(
        default=False,
        description="Whether this bot integration is enabled for the account.",
        examples=[True],
    )
    notify: bool = Field(
        default=False,
        description="Whether notifications through this bot are enabled.",
        examples=[True],
    )


class AccountSettingsSchema(CamelCaseSchema):
    model_config = ConfigDict(validate_default=True)

    language: AccountLanguageEnum = Field(
        default=AccountLanguageEnum.EN, description="Preferred interface language.", examples=["en"]
    )
    theme: AccountThemeEnum = Field(
        default=AccountThemeEnum.LIGHT,
        description="Preferred interface color theme.",
        examples=["dark"],
    )
    time_zone: AccountTimeZone = Field(
        default_factory=lambda: constants.account_time_zone.default,
        description="IANA time zone identifier used for the account calendar and reminders.",
        examples=["Asia/Yerevan"],
        json_schema_extra={
            "type": "string",
            "format": "iana-time-zone",
            "maxLength": constants.account_time_zone.max_iana_time_zone_length,
        },
    )
    telegram_bots: dict[TelegramBotId, TelegramBotSettingsSchema] = Field(
        default_factory=dict,
        description=(
            "Preferences keyed by supported bot identifier. Omitted bots use disabled defaults."
        ),
        examples=[{"personal-workspace": {"enabled": True, "notify": True}}],
    )

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


class CurrentAccountResponseSchema(CamelCaseSchema):
    username: str = Field(description="Unique account login name.", examples=["dmitriy.lunev"])
    role: RoleEnum = Field(
        description="Current account authorization role.", examples=["moderator"]
    )
    first_name: str | None = Field(description="Given name; null when unset.", examples=["Dmitriy"])
    last_name: str | None = Field(description="Family name; null when unset.", examples=["Lunev"])
    middle_name: str | None = Field(
        description="Middle name; null when unset.", examples=["Alexandrovich"]
    )
    gender: GenderEnum | None = Field(
        description="Profile gender; null when unset.", examples=["male"]
    )
    settings: AccountSettingsSchema = Field(description="Complete current account preferences.")
    has_avatar: bool = Field(
        description="Whether GET /api/auth/account/me/avatar has an avatar to return.",
        examples=[True],
    )

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
