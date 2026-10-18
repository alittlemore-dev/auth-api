from typing import Annotated, Literal, Self

from pydantic import Field

from core.auth.enums import RoleEnum
from core.auth.schemas import AccessTokenResult, AuthVerificationResult
from entrypoints.litestar.api.openapi import OPENAPI_PASSWORD_EXAMPLE
from entrypoints.litestar.api.schemas import CamelCaseSchema

PASETO_TOKEN_EXAMPLE = (
    "v4.public.eyJ1c2VybmFtZSI6ICJkbWl0cml5Lmx1bmV2IiwgInNlc3Npb25faWQiOiAiNzI0ZjlhYTNiOTg"  # noqa: S105  # nosec B105
    "0NGM4Yzg2N2VkNGUzMWM4MjBkYjIiLCAiZXhwIjogIjIwMjYtMTAtMThUMTI6MTU6MDArMDA6MDAifV-Kjzs_"
    "qUaxTt7e9DUGw_nYy01i50-MWxycJzlbLL8GJBmLgklCx-NZVp7plPwIpz9MUXgK-y1EGAFewpPA1Ac"
)


class AccessTokenResponseSchema(CamelCaseSchema):
    access_token: Annotated[
        str,
        Field(
            title="Access token",
            description=(
                "PASETO v4.public bearer access token; this illustrative token cannot authenticate."
            ),
            examples=[PASETO_TOKEN_EXAMPLE],
        ),
    ]
    access_token_expires_in_seconds: Annotated[
        int,
        Field(
            title="Access token expiration seconds",
            description="Short-lived PASETO access token lifetime in seconds.",
            examples=[900],
        ),
    ]

    @classmethod
    def from_domain_schema(cls, *, schema: AccessTokenResult) -> Self:
        return cls(
            access_token=schema.token.decode(),
            access_token_expires_in_seconds=schema.expires_in_seconds,
        )


class VerifyAccessTokenResponseSchema(CamelCaseSchema):
    username: str = Field(
        description="Authenticated account login name.", examples=["dmitriy.lunev"]
    )
    role: RoleEnum = Field(description="Current authorization role.", examples=["moderator"])
    valid_for_seconds: int = Field(
        description="Remaining credential lifetime in seconds.", examples=[840]
    )

    @classmethod
    def from_domain_schema(cls, *, schema: AuthVerificationResult) -> Self:
        return cls(
            username=schema.user.username,
            role=schema.user.role,
            valid_for_seconds=schema.valid_for_seconds,
        )


class LoginRequestSchema(CamelCaseSchema):
    username: Annotated[
        str,
        Field(description="Account login name.", examples=["dmitriy.lunev"]),
    ]
    password: Annotated[
        str,
        Field(
            description="Account password. Example is fictitious.",
            examples=[OPENAPI_PASSWORD_EXAMPLE],
            json_schema_extra={"format": "password"},
        ),
    ]


class VerifyCredentialResponseSchema(VerifyAccessTokenResponseSchema):
    credential_type: Literal["session", "pat"] = Field(
        description="Browser session or personal API token.", examples=["session"]
    )
    credential_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Identifier of the verified session or personal API token.",
            examples=["724f9aa3b9844c8c867ed4e31c820db2"],
        ),
    ]
    permissions: list[str] = Field(
        description="Sorted permission scopes for a personal API token; empty for a session.",
        examples=[["workspace.resumes.read"]],
    )
    cache_ttl_seconds: Annotated[
        int,
        Field(
            ge=0,
            description="Maximum verification cache lifetime; always zero for personal API tokens.",
            examples=[30],
        ),
    ]
