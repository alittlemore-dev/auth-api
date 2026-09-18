from typing import Annotated, Self

from backend_sdk import Principal
from pydantic import Field

from core.auth.enums import RoleEnum
from entrypoints.litestar.api.schemas import CamelCaseSchema


class GetBaseCurrentUserAccountResponseSchema(CamelCaseSchema):
    username: Annotated[
        str,
        Field(
            title="Username",
            description="Username",
            examples=["user1"],
        ),
    ]
    role: Annotated[
        RoleEnum,
        Field(
            title="User role",
            description="User role",
            examples=[RoleEnum.USER],
        ),
    ]

    @classmethod
    def from_principal(cls, *, principal: Principal) -> Self:
        return cls(
            username=principal.username,
            role=RoleEnum.from_value(principal.role.value),
        )
