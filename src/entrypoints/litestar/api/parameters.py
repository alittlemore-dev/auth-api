# ruff: noqa: UP040
# Litestar 2.23 does not unwrap PEP 695 aliases in handler signatures.
from typing import Annotated, TypeAlias

from litestar.enums import RequestEncodingType
from litestar.openapi.spec import Example
from litestar.params import BodyKwarg, PathParameter, QueryParameter


def build_examples(*values: object) -> list[Example]:
    return [Example(value=value) for value in values]


def api_query_parameter(  # noqa: PLR0913
    *,
    name: str,
    title: str,
    description: str,
    examples: tuple[object, ...],
    ge: float | None,
    le: float | None,
    min_items: int | None,
    max_items: int | None,
) -> QueryParameter:
    return QueryParameter(
        name=name,
        title=title,
        description=description,
        examples=build_examples(*examples),
        ge=ge,
        le=le,
        min_items=min_items,
        max_items=max_items,
        schema_extra={"examples": list(examples)},
    )


def api_path_parameter(
    *,
    name: str,
    title: str,
    description: str,
    examples: tuple[object, ...],
) -> PathParameter:
    return PathParameter(
        name=name,
        title=title,
        description=description,
        examples=build_examples(*examples),
        schema_extra={"examples": list(examples)},
    )


def api_json_body(
    *,
    title: str,
    description: str,
    examples: tuple[object, ...],
) -> BodyKwarg:
    return BodyKwarg(
        title=title,
        description=description,
        examples=build_examples(*examples),
        media_type=RequestEncodingType.JSON,
        schema_extra={"examples": list(examples)},
    )


PageQuery: TypeAlias = Annotated[
    int,
    api_query_parameter(
        name="page",
        title="Page",
        description="One-based page number.",
        examples=(1,),
        ge=1,
        le=None,
        min_items=None,
        max_items=None,
    ),
]
PageSizeQuery: TypeAlias = Annotated[
    int,
    api_query_parameter(
        name="pageSize",
        title="Page size",
        description="Number of items to return per page.",
        examples=(20,),
        ge=1,
        le=100,
        min_items=None,
        max_items=None,
    ),
]
UsernamePath: TypeAlias = Annotated[
    str,
    api_path_parameter(
        name="username",
        title="Username",
        description="Managed account username.",
        examples=("moderator",),
    ),
]
SessionIdPath: TypeAlias = Annotated[
    str,
    api_path_parameter(
        name="session_id",
        title="Session identifier",
        description="Hex identifier of the managed account session.",
        examples=("00000000000000000000000000000001",),
    ),
]
