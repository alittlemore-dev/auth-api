# ruff: noqa: S106
from sqlalchemy import MetaData, Table, create_engine, inspect, select

from infra.config.settings import Settings
from infra.postgresql.utils import downgrade, migrate


def test_settings_upgrade_existing_users_and_downgrade(
    migrated_to_0001: None,
    test_settings: Settings,
) -> None:
    _ = migrated_to_0001
    migrate(revision="0002")
    engine = create_engine(test_settings.database.url.get_secret_value())
    users = Table("auth__user_model", MetaData(), autoload_with=engine)
    try:
        with engine.begin() as connection:
            connection.execute(
                users.insert().values(
                    username="settings-user",
                    password_hash="hash",
                    role="USER",
                    is_active=True,
                )
            )
        migrate(revision="0003")
        updated = Table("auth__user_model", MetaData(), autoload_with=engine)
        assert updated.c.settings.nullable is False
        with engine.begin() as connection:
            assert (
                connection.scalar(
                    select(updated.c.settings).where(updated.c.username == "settings-user")
                )
                == {}
            )
            connection.execute(
                updated.insert().values(
                    username="new-user",
                    password_hash="hash",
                    role="USER",
                    is_active=True,
                )
            )
            assert (
                connection.scalar(
                    select(updated.c.settings).where(updated.c.username == "new-user")
                )
                == {}
            )
        downgrade(revision="0002")
        assert "settings" not in {
            column["name"] for column in inspect(engine).get_columns("auth__user_model")
        }
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    select(users.c.username).where(users.c.username == "settings-user")
                )
                == "settings-user"
            )
    finally:
        downgrade(revision="0002")
        with engine.begin() as connection:
            connection.execute(users.delete())
        engine.dispose()
