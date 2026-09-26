import pytest
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy_dev_utils.types.pydantic import PydanticType

from core.account.enums import TelegramBotId
from entrypoints.litestar.api.account.schemas import AccountSettingsSchema as ApiSettings
from infra.postgresql.schemas import AccountSettingsSchema


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        (AccountSettingsSchema, {"language": "en", "theme": "light", "telegram_bots": {}}),
        (ApiSettings, {"language": "en", "theme": "light", "telegram_bots": {}}),
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
        "telegram_bots": {},
    }
    assert (
        adapter.process_result_value(adapter.process_bind_param(partial, dialect()), dialect())
        == partial
    )


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
