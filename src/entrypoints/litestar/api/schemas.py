from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel as camel_case
from pydantic.alias_generators import to_snake as snake_case


class CamelCaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=camel_case,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
    )


class SnakeCaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=snake_case,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
    )


class DetailResponseSchema(CamelCaseSchema):
    detail: Annotated[
        str,
        Field(
            title="Message",
            description="Detailed operation result description",
            examples=["Operation completed successfully"],
        ),
    ]
