# ruff: noqa: S106
from datetime import UTC, datetime, timedelta

from sqlalchemy import MetaData, Table, create_engine, inspect, select

from infra.config.settings import Settings
from infra.postgresql.utils import downgrade, migrate


def test_api_tokens_upgrade_cascade_and_downgrade(
    migrated_to_0001: None,
    test_settings: Settings,
) -> None:
    _ = migrated_to_0001
    migrate(revision="0003")
    engine = create_engine(test_settings.database.url.get_secret_value())
    users = Table("auth__user_model", MetaData(), autoload_with=engine)
    try:
        with engine.begin() as connection:
            connection.execute(
                users.insert().values(
                    username="pat-user", password_hash="hash", role="USER", is_active=True
                )
            )
        migrate(revision="0004")
        tokens = Table("api_tokens__api_token_model", MetaData(), autoload_with=engine)
        now = datetime.now(tz=UTC)
        with engine.begin() as connection:
            connection.execute(
                tokens.insert().values(
                    username="pat-user",
                    name="test",
                    permissions=["auth.account.read"],
                    secret_hash="a" * 64,
                    secret="encrypted-test-data",
                    created_at=now,
                    expires_at=now + timedelta(hours=1),
                )
            )
            assert connection.scalar(select(tokens.c.username)) == "pat-user"
            connection.execute(users.delete().where(users.c.username == "pat-user"))
            assert connection.scalar(select(tokens.c.id)) is None
        downgrade(revision="0003")
        assert "api_tokens__api_token_model" not in inspect(engine).get_table_names()
    finally:
        downgrade(revision="0003")
        with engine.begin() as connection:
            connection.execute(users.delete())
        engine.dispose()
