from ipaddress import IPv4Address
from typing import Literal

from pydantic import PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.schemas import Secret
from infra.config.constants import constants

_LOCAL_ALL_INTERFACES_HOST = IPv4Address(0).compressed


class ProjectBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=constants.path.env_file, extra="ignore")


class SecretStrExtended(SecretStr):
    def to_domain_secret(self) -> Secret[str]:
        return Secret(self.get_secret_value())


class DatabaseSettings(ProjectBaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_")

    user: str
    password: SecretStrExtended
    driver: str
    host: str
    port: str
    name: str
    pool_pre_ping: bool
    pool_size: int
    max_overflow: int
    expire_on_commit: bool
    log_query_metrics: bool
    slow_query_log_threshold_ms: int
    slow_query_log_statement_max_length: int

    @property
    def url(self) -> SecretStrExtended:
        return SecretStrExtended(
            f"{self.driver}://{self.user}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.name}",
        )


class AppSettings(ProjectBaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    url_schema: Literal["http", "https"]
    debug: bool
    secret_key: SecretStrExtended
    domain: str

    @property
    def is_local_domain(self) -> bool:
        return self.domain in {"localhost", "127.0.0.1", _LOCAL_ALL_INTERFACES_HOST}

    @property
    def base_url(self) -> str:
        postfix = ":8000" if self.debug and self.is_local_domain else ""
        return f"{self.url_schema}://{self.domain}{postfix}"

    @property
    def public_origin(self) -> str:
        return f"{self.url_schema}://{self.domain}"

    def get_url(self, path: str) -> str:
        return f"{self.base_url}/{path.removeprefix('/')}"


class OwnerSettings(ProjectBaseSettings):
    model_config = SettingsConfigDict(env_prefix="OWNER_")

    init_login: str
    init_password: SecretStrExtended


class AuthSettings(ProjectBaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTH_")

    public_key: SecretStrExtended
    private_key: SecretStrExtended
    token_expire_seconds: int
    session_expire_seconds: int
    session_absolute_expire_seconds: int
    token_header_name: str
    token_prefix: str


class SentrySettings(ProjectBaseSettings):
    model_config = SettingsConfigDict(env_prefix="SENTRY_")

    use: bool
    dsn: str


class ValkeySettings(ProjectBaseSettings):
    model_config = SettingsConfigDict(env_prefix="VALKEY_")

    host: str
    port: int

    def get_url(self, db: int | str) -> SecretStrExtended:
        return SecretStrExtended(f"valkey://{self.host}:{self.port}/{db}")


class TaskiqSettings(ProjectBaseSettings):
    model_config = SettingsConfigDict(env_prefix="TASKIQ_")

    auth_session_prune_interval_seconds: PositiveInt
    result_expire_seconds: PositiveInt


class Settings:
    app: AppSettings
    auth: AuthSettings
    database: DatabaseSettings
    owner: OwnerSettings
    sentry: SentrySettings
    taskiq: TaskiqSettings
    valkey: ValkeySettings

    def __init__(self) -> None:
        self.app = AppSettings()
        self.auth = AuthSettings()
        self.database = DatabaseSettings()
        self.owner = OwnerSettings()
        self.sentry = SentrySettings()
        self.taskiq = TaskiqSettings()
        self.valkey = ValkeySettings()


settings = Settings()
