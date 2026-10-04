from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, ConfigDict, Field, SecretStr

from core.api_tokens.schemas import ApiPermission, ApiToken, ApiTokenCreate
from entrypoints.litestar.api.schemas import CamelCaseSchema


class ApiTokenPasswordSchema(CamelCaseSchema):
    model_config = ConfigDict(hide_input_in_errors=True)
    password: Annotated[SecretStr, Field(min_length=1, max_length=1024)]


class ApiTokenCreateSchema(ApiTokenPasswordSchema):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    permissions: Annotated[list[str], Field(min_length=1, max_length=128)]
    expires_at: AwareDatetime

    def to_domain_schema(self) -> ApiTokenCreate:
        return ApiTokenCreate(
            name=self.name,
            permissions=frozenset(self.permissions),
            expires_at=self.expires_at,
        )


class ApiTokenMetadataSchema(CamelCaseSchema):
    id: str
    name: str
    permissions: list[str]
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    status: str

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
    tokens: list[ApiTokenMetadataSchema]


class ApiTokenSecretSchema(CamelCaseSchema):
    secret: str


class ApiTokenCreatedSchema(ApiTokenSecretSchema):
    token: ApiTokenMetadataSchema


class ApiPermissionSchema(CamelCaseSchema):
    code: str
    service: str
    domain: str
    action: str

    @classmethod
    def from_domain_schema(cls, schema: ApiPermission) -> ApiPermissionSchema:
        return cls(
            code=schema.code, service=schema.service, domain=schema.domain, action=schema.action
        )


class ApiPermissionsSchema(CamelCaseSchema):
    permissions: list[ApiPermissionSchema]
