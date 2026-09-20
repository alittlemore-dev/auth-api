from pathlib import Path
from typing import Literal


class PathConstants:
    src_dir: Path = Path(__file__).resolve().parent.parent.parent
    root_dir: Path = src_dir.parent
    env_file: Path = root_dir / ".env"
    infra_dir: Path = src_dir / "infra"
    alembic_dir: Path = infra_dir / "postgresql" / "alembic"


class ValkeyDatabaseConstants:
    auth_revocations: int = 1
    taskiq_broker: int = 3
    taskiq_results: int = 4


class ValkeyNamespaceConstants:
    auth_revocations: str = "AUTH_REVOCATIONS"


class ValkeyConstants:
    databases: ValkeyDatabaseConstants = ValkeyDatabaseConstants()
    namespaces: ValkeyNamespaceConstants = ValkeyNamespaceConstants()
    missing_ttl_seconds: int = -2
    non_expiring_ttl_seconds: int = -1


class TaskiqConstants:
    queue_name: Literal["auth_api_background"] = "auth_api_background"
    consumer_group_name: Literal["auth_api_background"] = "auth_api_background"
    result_prefix: Literal["auth_api_taskiq_results"] = "auth_api_taskiq_results"
    auth_session_prune_task_name: Literal["auth_session_prune"] = "auth_session_prune"
    account_avatar_orphan_prune_task_name: Literal["account_avatar_orphan_prune"] = (
        "account_avatar_orphan_prune"
    )


class AccountAvatarConstants:
    max_source_bytes: int = 5 * 1024 * 1024
    supported_mime_types: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})
    max_decoded_pixels: int = 25_000_000
    output_size_pixels: int = 512
    webp_quality: int = 90
    webp_method: int = 6
    stream_chunk_size: int = 64 * 1024
    private_bucket_name: Literal["auth-avatars"] = "auth-avatars"
    orphan_retention_seconds: int = 24 * 60 * 60


class AdminValidationConstants:
    account_username_pattern: str = r"^[A-Za-z0-9._]+$"
    account_username_min_length: int = 3
    account_password_min_length: int = 8
    short_text_max_length: int = 255


class AuthConstants:
    session_cookie_name: Literal["__Secure-msid"] = "__Secure-msid"
    session_cookie_path: Literal["/api/auth"] = "/api/auth"
    csrf_guard_header_name: Literal["X-CSRF-Guard"] = "X-CSRF-Guard"
    csrf_guard_header_value: Literal["1"] = "1"
    fetch_metadata_site_header_name: Literal["Sec-Fetch-Site"] = "Sec-Fetch-Site"
    fetch_metadata_cross_site_value: Literal["cross-site"] = "cross-site"
    no_store_header_value: Literal["no-store"] = "no-store"
    session_secret_byte_count: int = 32
    session_expiring_soon_days: int = 7


class Constants:
    path: PathConstants = PathConstants()
    valkey: ValkeyConstants = ValkeyConstants()
    taskiq: TaskiqConstants = TaskiqConstants()
    account_avatar: AccountAvatarConstants = AccountAvatarConstants()
    admin_validation: AdminValidationConstants = AdminValidationConstants()
    auth: AuthConstants = AuthConstants()


constants = Constants()
