from typing import Annotated

from pydantic import Field, field_validator

from core.account.schemas import (
    ManagedAccount,
    ManagedAccountCreateParams,
    ManagedAccountPasswordUpdateParams,
    ManagedAccountRoleUpdateParams,
    ManagedAccounts,
    ManagedAccountSession,
    ManagedAccountSessionRevocationResult,
    ManagedAccountSessions,
)
from core.auth.enums import RoleEnum
from core.schemas import Secret
from entrypoints.litestar.api.schemas import CamelCaseSchema
from entrypoints.litestar.api.validation import AccountPasswordString, AccountUsernameString


class ManagedAccountRoleMixin(CamelCaseSchema):
    role: Annotated[
        RoleEnum,
        Field(
            title="Managed account role",
            description="Only admin and moderator can be assigned.",
            examples=["moderator"],
        ),
    ]

    @field_validator("role")
    @classmethod
    def validate_managed_role(cls, value: RoleEnum) -> RoleEnum:
        if value not in {RoleEnum.ADMIN, RoleEnum.MODERATOR}:
            msg = "role must be admin or moderator"
            raise ValueError(msg)
        return value


class ManagedAccountCreateRequestSchema(ManagedAccountRoleMixin):
    username: Annotated[
        AccountUsernameString,
        Field(title="Username", description="Unique account login name.", examples=["moderator"]),
    ]
    password: Annotated[
        AccountPasswordString,
        Field(
            title="Password",
            json_schema_extra={"format": "password"},
            description="Account password. Example is fictitious.",
            examples=["Example-Password-42!"],
        ),
    ]
    is_active: Annotated[
        bool,
        Field(title="Active", description="Whether the account can authenticate.", examples=[True]),
    ]

    def to_domain_schema(self) -> ManagedAccountCreateParams:
        return ManagedAccountCreateParams(
            username=self.username,
            role=self.role,
            password=Secret(self.password),
            is_active=self.is_active,
        )


class ManagedAccountRoleUpdateRequestSchema(ManagedAccountRoleMixin):
    def to_domain_schema(self) -> ManagedAccountRoleUpdateParams:
        return ManagedAccountRoleUpdateParams(role=self.role)


class ManagedAccountPasswordUpdateRequestSchema(CamelCaseSchema):
    password: Annotated[
        AccountPasswordString,
        Field(
            title="Password",
            json_schema_extra={"format": "password"},
            description="Account password. Example is fictitious.",
            examples=["Example-Password-42!"],
        ),
    ]

    def to_domain_schema(self) -> ManagedAccountPasswordUpdateParams:
        return ManagedAccountPasswordUpdateParams(password=Secret(self.password))


class ManagedAccountResponseSchema(CamelCaseSchema):
    username: Annotated[
        str,
        Field(title="Username", description="Unique account login name.", examples=["moderator"]),
    ]
    role: Annotated[
        RoleEnum,
        Field(title="Role", description="Current authorization role.", examples=["moderator"]),
    ]
    is_active: Annotated[
        bool,
        Field(title="Active", description="Whether the account can authenticate.", examples=[True]),
    ]

    @classmethod
    def from_domain_schema(cls, *, schema: ManagedAccount) -> ManagedAccountResponseSchema:
        return cls.model_construct(
            username=schema.username,
            role=schema.role,
            is_active=schema.is_active,
        )


class ManagedAccountsResponseSchema(CamelCaseSchema):
    total_count: Annotated[
        int,
        Field(
            title="Total count",
            description="Total managed accounts matching this list.",
            examples=[37],
        ),
    ]
    total_pages: Annotated[
        int,
        Field(
            title="Total pages",
            description="Number of pages for the requested pageSize; zero for an empty list.",
            examples=[2],
        ),
    ]
    accounts: Annotated[
        list[ManagedAccountResponseSchema],
        Field(
            title="Accounts",
            description="Accounts on the requested page; empty if the page is beyond the end.",
        ),
    ]

    @classmethod
    def from_domain_schema(cls, *, schema: ManagedAccounts) -> ManagedAccountsResponseSchema:
        return cls.model_construct(
            total_count=schema.total_count,
            total_pages=schema.total_pages,
            accounts=[
                ManagedAccountResponseSchema.from_domain_schema(schema=account)
                for account in schema.values
            ],
        )


class ManagedAccountSessionResponseSchema(CamelCaseSchema):
    id: Annotated[
        str,
        Field(
            title="Session ID",
            description="Opaque server-side session identifier.",
            examples=["724f9aa3b9844c8c867ed4e31c820db2"],
        ),
    ]
    user_agent_display: Annotated[
        str,
        Field(
            title="User-agent display",
            description="Readable browser and operating system summary.",
            examples=["Firefox 143 on Linux"],
        ),
    ]
    user_agent_browser: Annotated[
        str,
        Field(
            title="User-agent browser",
            description="Parsed browser name/version.",
            examples=["Firefox 143"],
        ),
    ]
    user_agent_os: Annotated[
        str,
        Field(title="User-agent OS", description="Parsed operating system.", examples=["Linux"]),
    ]
    user_agent_device: Annotated[
        str,
        Field(
            title="User-agent device", description="Parsed device category.", examples=["desktop"]
        ),
    ]
    auth_method: Annotated[
        str,
        Field(
            title="Authentication method",
            description="Method that created the session.",
            examples=["password"],
        ),
    ]
    created_at: Annotated[
        str,
        Field(
            title="Created at",
            description="Session creation time as an ISO 8601 UTC timestamp.",
            examples=["2026-10-18T12:00:00+00:00"],
        ),
    ]
    last_used_at: Annotated[
        str,
        Field(
            title="Last used at",
            description="Last successful session activity as an ISO 8601 UTC timestamp.",
            examples=["2026-10-18T13:15:00+00:00"],
        ),
    ]
    expires_at: Annotated[
        str,
        Field(
            title="Expires at",
            description="Session expiry as an ISO 8601 UTC timestamp.",
            examples=["2026-11-17T12:00:00+00:00"],
        ),
    ]
    is_current: Annotated[
        bool,
        Field(
            title="Current session",
            description=(
                "Whether the session is the browser session used for this request; false "
                "for a PAT request."
            ),
            examples=[True],
        ),
    ]

    @classmethod
    def from_domain_schema(
        cls,
        *,
        schema: ManagedAccountSession,
    ) -> ManagedAccountSessionResponseSchema:
        return cls.model_construct(
            id=schema.id,
            user_agent_display=schema.client_metadata.user_agent_display,
            user_agent_browser=schema.client_metadata.user_agent_browser,
            user_agent_os=schema.client_metadata.user_agent_os,
            user_agent_device=schema.client_metadata.user_agent_device.value,
            auth_method=schema.auth_method.value,
            created_at=schema.created_at.isoformat(),
            last_used_at=schema.last_used_at.isoformat(),
            expires_at=schema.expires_at.isoformat(),
            is_current=schema.is_current,
        )


class ManagedAccountSessionsResponseSchema(CamelCaseSchema):
    sessions: Annotated[
        list[ManagedAccountSessionResponseSchema],
        Field(title="Sessions", description="Active sessions of the managed account."),
    ]

    @classmethod
    def from_domain_schema(
        cls,
        *,
        schema: ManagedAccountSessions,
    ) -> ManagedAccountSessionsResponseSchema:
        return cls.model_construct(
            sessions=[
                ManagedAccountSessionResponseSchema.from_domain_schema(schema=session)
                for session in schema.values
            ],
        )


class ManagedAccountSessionRevocationResponseSchema(CamelCaseSchema):
    current_session_revoked: Annotated[
        bool,
        Field(
            title="Current session revoked",
            description="Whether this action revoked the browser session making the request.",
            examples=[False],
        ),
    ]

    @classmethod
    def from_domain_schema(
        cls,
        *,
        schema: ManagedAccountSessionRevocationResult,
    ) -> ManagedAccountSessionRevocationResponseSchema:
        return cls.model_construct(current_session_revoked=schema.current_session_revoked)
