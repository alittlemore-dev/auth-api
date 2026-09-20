# ruff: noqa: S106
from sqlalchemy import MetaData, Table, create_engine, inspect, select
from sqlalchemy.dialects.postgresql.base import PGInspector
from sqlalchemy.sql.sqltypes import Text

from infra.config.settings import Settings
from infra.postgresql.utils import downgrade, migrate

PROFILE_COLUMN_NAMES = {
    "first_name",
    "last_name",
    "middle_name",
    "gender",
    "avatar_object_name",
}


def test_profile_columns_upgrade_existing_user_and_round_trip_downgrade(
    migrated_to_0001: None,
    test_settings: Settings,
) -> None:
    _ = migrated_to_0001
    engine = create_engine(test_settings.database.url.get_secret_value())
    metadata = MetaData()
    users = Table("auth__user_model", metadata, autoload_with=engine)
    try:
        with engine.begin() as connection:
            connection.execute(
                users.insert().values(
                    username="existing-user",
                    password_hash="hash",
                    role="USER",
                    is_active=True,
                ),
            )

        migrate(revision="0002")
        inspector = inspect(engine)
        assert isinstance(inspector, PGInspector)
        columns = {
            column["name"]: column
            for column in inspector.get_columns("auth__user_model")
            if column["name"] in PROFILE_COLUMN_NAMES
        }
        assert set(columns) == PROFILE_COLUMN_NAMES
        assert all(column["nullable"] for column in columns.values())
        assert all(
            isinstance(columns[name]["type"], Text)
            for name in ("first_name", "last_name", "middle_name", "gender")
        )

        upgraded_users = Table("auth__user_model", MetaData(), autoload_with=engine)
        with engine.connect() as connection:
            row = connection.execute(
                select(
                    upgraded_users.c.first_name,
                    upgraded_users.c.last_name,
                    upgraded_users.c.middle_name,
                    upgraded_users.c.gender,
                    upgraded_users.c.avatar_object_name,
                ).where(upgraded_users.c.username == "existing-user"),
            ).one()
        assert tuple(row) == (None, None, None, None, None)

        downgrade(revision="0001")
        remaining_names = {
            column["name"] for column in inspect(engine).get_columns("auth__user_model")
        }
        assert PROFILE_COLUMN_NAMES.isdisjoint(remaining_names)
        migrate(revision="0002")
        assert {
            column["name"] for column in inspect(engine).get_columns("auth__user_model")
        } >= PROFILE_COLUMN_NAMES
    finally:
        downgrade(revision="0001")
        with engine.begin() as connection:
            connection.execute(users.delete())
        engine.dispose()
