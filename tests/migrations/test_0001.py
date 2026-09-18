import pytest
from sqlalchemy import (
    Boolean,
    Column,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    inspect,
    select,
)
from sqlalchemy.dialects.postgresql.base import PGInspector

from infra.config.settings import Settings
from infra.postgresql.utils import downgrade, migrate


def test_initial_schema_has_no_users_and_supports_upgrade_downgrade_roundtrip(
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OWNER_INIT_LOGIN", "legacy-owner")
    monkeypatch.setenv("OWNER_INIT_PASSWORD", "legacy-password")
    engine = create_engine(test_settings.database.url.get_secret_value())
    owner_table = Table(
        "auth__user_model",
        MetaData(),
        Column("username", String),
        Column("password_hash", String),
        Column("role", String),
        Column("is_active", Boolean),
    )
    enum_names = {"role_enum", "auth_session_auth_method_enum", "auth_session_device_type_enum"}
    try:
        for _ in range(2):
            migrate(revision="0001")
            with engine.connect() as connection:
                inspector = inspect(connection)
                assert isinstance(inspector, PGInspector)
                assert set(inspector.get_table_names()) == {
                    "alembic_version",
                    "auth__user_model",
                    "auth__auth_session_model",
                }
                assert {item["name"] for item in inspector.get_enums()} == enum_names
                assert (
                    connection.execute(select(func.count()).select_from(owner_table)).scalar_one()
                    == 0
                )
            migrate(revision="head")
            downgrade(revision="base")
            with engine.connect() as connection:
                inspector = inspect(connection)
                assert isinstance(inspector, PGInspector)
                assert inspector.get_table_names() == ["alembic_version"]
                assert inspector.get_enums() == []
    finally:
        downgrade(revision="base")
        engine.dispose()
