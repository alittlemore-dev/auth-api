from dataclasses import dataclass

from core.api_tokens.schemas import ApiPermission
from core.auth.enums import RoleEnum
from core.auth.schemas import BaseUser

# The registry is finite; each action represents a supported API operation.
PERMISSION_DOMAINS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("auth", "account", "user", ("read", "update", "delete")),
    (
        "auth",
        "accounts",
        "admin",
        ("read", "create", "delete", "password", "role", "activate", "deactivate"),
    ),
    ("auth", "sessions", "admin", ("read", "revoke")),
    ("auth", "tools", "admin", ("read", "manage")),
    ("workspace", "resumes", "user", ("read", "create", "update", "delete")),
    ("workspace", "files", "user", ("read", "create", "update", "delete")),
    ("workspace", "knowledge", "user", ("read", "create", "update", "delete")),
    ("workspace", "events", "user", ("read", "create", "update", "delete")),
    ("workspace", "calendar", "user", ("read",)),
    ("workspace", "finance", "user", ("read", "create", "update", "delete")),
    ("workspace", "vault", "user", ("read",)),
    ("workspace", "important_info", "user", ("read", "create", "update", "delete")),
    ("workspace", "wiki_links", "user", ("read",)),
    ("workspace", "telegram", "user", ("read", "create", "update", "delete")),
    ("workspace", "tools", "admin", ("read", "manage")),
    ("competency", "articles", "user", ("record_view",)),
    ("competency", "matrix", "user", ("suggest",)),
    ("competency", "articles", "moderator", ("read", "create", "update", "delete", "publish")),
    ("competency", "matrix", "moderator", ("read", "create", "update", "delete", "publish")),
    ("competency", "files", "moderator", ("read", "create", "update", "delete")),
    ("competency", "wiki_links", "moderator", ("read",)),
    ("competency", "tools", "admin", ("read", "manage")),
)


@dataclass(frozen=True, slots=True)
class ApiPermissionRegistry:
    permissions: tuple[ApiPermission, ...] = tuple(
        ApiPermission(
            code=f"{service}.{domain}.{action}",
            service=service,
            domain=domain,
            action=action,
            minimum_role=role,
        )
        for service, domain, role, actions in PERMISSION_DOMAINS
        for action in actions
    )

    def allowed_for(self, *, user: BaseUser) -> tuple[ApiPermission, ...]:
        return tuple(
            permission
            for permission in self.permissions
            if user.has_role(RoleEnum.from_value(permission.minimum_role))
        )

    def codes_for(self, *, user: BaseUser) -> frozenset[str]:
        return frozenset(permission.code for permission in self.allowed_for(user=user))
