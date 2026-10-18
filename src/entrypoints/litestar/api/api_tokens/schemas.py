from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, ConfigDict, Field, SecretStr

from core.api_tokens.schemas import ApiPermission, ApiToken, ApiTokenCreate
from entrypoints.litestar.api.openapi import OPENAPI_PASSWORD_EXAMPLE
from entrypoints.litestar.api.schemas import CamelCaseSchema


class ApiTokenPasswordSchema(CamelCaseSchema):
    model_config = ConfigDict(hide_input_in_errors=True)
    password: Annotated[
        SecretStr,
        Field(
            min_length=1,
            max_length=1024,
            description="Current account password, required for every create/reveal request.",
            examples=[OPENAPI_PASSWORD_EXAMPLE],
        ),
    ]


class ApiTokenCreateSchema(ApiTokenPasswordSchema):
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="Human-readable token label.",
            examples=["Resume sync CLI"],
        ),
    ]
    permissions: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=128,
            description=(
                "Permission scopes from the permissions endpoint; immutable after creation."
            ),
            examples=[["workspace.resumes.read"]],
        ),
    ]
    expires_at: AwareDatetime = Field(
        description=(
            "Timezone-aware expiry strictly after now and at most 365 days away; immutable."
        ),
        examples=["2027-01-18T12:00:00Z"],
    )

    def to_domain_schema(self) -> ApiTokenCreate:
        return ApiTokenCreate(
            name=self.name,
            permissions=frozenset(self.permissions),
            expires_at=self.expires_at,
        )


class ApiTokenMetadataSchema(CamelCaseSchema):
    id: str = Field(
        description="Opaque token identifier, not the bearer secret.",
        examples=["724f9aa3b9844c8c867ed4e31c820db2"],
    )
    name: str = Field(description="Human-readable token label.", examples=["Resume sync CLI"])
    permissions: list[str] = Field(
        description="Sorted scopes granted to this token.", examples=[["workspace.resumes.read"]]
    )
    created_at: datetime = Field(
        description="Token creation time in UTC.", examples=["2026-10-18T12:00:00Z"]
    )
    expires_at: datetime = Field(
        description="Token expiry time in UTC.", examples=["2027-01-18T12:00:00Z"]
    )
    last_used_at: datetime | None = Field(
        description="Last successful authentication time; null until used.",
        examples=["2026-10-18T13:15:00Z"],
    )
    revoked_at: datetime | None = Field(
        description="Revocation time; null while not revoked.", examples=[None]
    )
    status: str = Field(
        description="Current status: active, expired or revoked.", examples=["active"]
    )

    @classmethod
    def from_domain_schema(cls, *, schema: ApiToken, now: datetime) -> ApiTokenMetadataSchema:
        return cls(
            id=schema.id,
            name=schema.name,
            permissions=sorted(schema.permissions),
            created_at=schema.created_at,
            expires_at=schema.expires_at,
            last_used_at=schema.last_used_at,
            revoked_at=schema.revoked_at,
            status=schema.status_at(now=now),
        )


class ApiTokenListSchema(CamelCaseSchema):
    tokens: list[ApiTokenMetadataSchema] = Field(
        description="All personal API tokens owned by the account, without secrets."
    )


class ApiTokenSecretSchema(CamelCaseSchema):
    secret: str = Field(
        description=(
            "Sensitive personal API bearer token. Store securely; sent only on create or "
            "password-confirmed reveal."
        ),
        examples=["alm_pat_4vD8QLV8vOX75vyR5RjOYK3-6Q8dmV7zDly9wv2zyW4"],
    )


class ApiTokenCreatedSchema(ApiTokenSecretSchema):
    token: ApiTokenMetadataSchema = Field(description="Metadata of the newly created token.")


class ApiPermissionSchema(CamelCaseSchema):
    code: str = Field(
        description="Complete permission scope used when creating a token.",
        examples=["workspace.resumes.read"],
    )
    service: str = Field(description="Service that owns this permission.", examples=["workspace"])
    domain: str = Field(
        description="Resource domain covered by this permission.", examples=["resumes"]
    )
    action: str = Field(description="Allowed action on the resource domain.", examples=["read"])

    @classmethod
    def from_domain_schema(cls, schema: ApiPermission) -> ApiPermissionSchema:
        return cls(
            code=schema.code, service=schema.service, domain=schema.domain, action=schema.action
        )


class ApiPermissionsSchema(CamelCaseSchema):
    permissions: list[ApiPermissionSchema] = Field(
        description="Permission catalog filtered to the current account role."
    )
