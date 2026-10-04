from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql.psycopg2 import dialect
from sqlalchemy_dev_utils.types.pydantic import PydanticType

from core.account.enums import TelegramBotId
from entrypoints.litestar.api.account.schemas import AccountSettingsSchema as ApiSettings
from infra.postgresql.schemas import AccountSettingsSchema


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        (
            AccountSettingsSchema,
            {"language": "en", "theme": "light", "time_zone": "UTC", "telegram_bots": {}},
        ),
        (
            ApiSettings,
            {"language": "en", "theme": "light", "time_zone": "UTC", "telegram_bots": {}},
        ),
    ],
)
def test_every_setting_has_a_valid_default(
    schema: type[AccountSettingsSchema | ApiSettings],
    expected: dict[str, object],
) -> None:
    assert all(not field.is_required() for field in schema.model_fields.values())
    assert schema().model_dump(mode="json") == expected


def test_json_adapter_restores_missing_defaults_and_round_trips() -> None:
    adapter = PydanticType(AccountSettingsSchema)
    restore = adapter.result_processor(dialect(), None)
    assert restore is not None
    assert restore("{}") == AccountSettingsSchema()
    partial = restore('{"theme": "dark"}')
    assert partial is not None
    assert partial.model_dump(mode="json") == {
        "language": "en",
        "theme": "dark",
        "time_zone": "UTC",
        "telegram_bots": {},
    }
    assert (
        adapter.process_result_value(adapter.process_bind_param(partial, dialect()), dialect())
        == partial
    )


def test_time_zone_survives_api_domain_and_json_adapters() -> None:
    api = ApiSettings.model_validate(
        {
            "language": "ru",
            "theme": "dark",
            "timeZone": "Asia/Yerevan",
            "telegramBots": {"personal-workspace": {"enabled": True, "notify": True}},
        },
    )
    domain = api.to_domain_schema()
    assert domain.time_zone == ZoneInfo("Asia/Yerevan")
    stored = AccountSettingsSchema.from_domain_schema(domain)
    adapter = PydanticType(AccountSettingsSchema)
    restored = adapter.process_result_value(
        adapter.process_bind_param(stored, dialect()),
        dialect(),
    )

    assert isinstance(restored, AccountSettingsSchema)
    assert restored.time_zone == ZoneInfo("Asia/Yerevan")
    assert restored.model_dump(mode="json")["time_zone"] == "Asia/Yerevan"
    assert restored.to_domain_schema() == domain
    assert ApiSettings.from_domain_schema(restored.to_domain_schema()).model_dump(
        mode="json",
        by_alias=True,
    ) == api.model_dump(mode="json", by_alias=True)
    assert api.model_dump(mode="json", by_alias=True)["timeZone"] == "Asia/Yerevan"


@pytest.mark.parametrize("value", ["", "Europe/NoSuchCity", "/etc/passwd", "x" * 256])
def test_invalid_time_zones_are_rejected_at_api_and_storage_boundaries(value: str) -> None:
    with pytest.raises(ValidationError):
        ApiSettings.model_validate({"timeZone": value})
    with pytest.raises(ValidationError):
        AccountSettingsSchema.model_validate({"time_zone": value})


def test_null_time_zone_is_rejected_in_api_and_storage() -> None:
    with pytest.raises(ValidationError):
        ApiSettings.model_validate({"timeZone": None})
    with pytest.raises(ValidationError):
        AccountSettingsSchema.model_validate({"time_zone": None})


def test_telegram_bot_keys_are_explicit_enum_values() -> None:
    schema = AccountSettingsSchema.model_validate(
        {"telegram_bots": {"personal-workspace": {"enabled": True}}},
    )
    assert schema.telegram_bots[TelegramBotId.PERSONAL_WORKSPACE].enabled
    assert not schema.telegram_bots[TelegramBotId.PERSONAL_WORKSPACE].notify
    assert schema.model_dump(mode="json")["telegram_bots"] == {
        "personal-workspace": {"enabled": True, "notify": False},
    }
    with pytest.raises(ValidationError):
        AccountSettingsSchema.model_validate(
            {"telegram_bots": {"unknown-bot": {"enabled": True}}},
        )


@pytest.mark.parametrize("value", [{"language": None}, {"theme": "system"}, {"language": "fr"}])
def test_json_adapter_rejects_invalid_settings(value: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AccountSettingsSchema.model_validate(value)
