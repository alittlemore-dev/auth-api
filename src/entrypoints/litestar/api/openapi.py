from typing import Any

from litestar.openapi import ResponseSpec
from litestar.openapi.spec import Example
from verbose_http_exceptions import error_by_status_mapping
from verbose_http_exceptions.exc.base import VerboseHTTPExceptionDict


class JSONExample(Example):
    def to_schema(self) -> dict[str, Any]:
        result = super().to_schema()
        # Litestar removes null dictionary entries, including required nullable JSON fields.
        if self.value is not None:
            result["value"] = self.value
        return result


def error_responses(**descriptions: str) -> dict[int, ResponseSpec]:
    return {
        int(status): ResponseSpec(
            data_container=VerboseHTTPExceptionDict,
            description=description,
            generate_examples=False,
            examples=[JSONExample(value=error_by_status_mapping[int(status)]().as_dict())],
        )
        for status, description in {
            "500": "Unexpected service or storage failure.",
            **descriptions,
        }.items()
    }


OPENAPI_PASSWORD_EXAMPLE = "Example-Password-42!"  # noqa: S105  # nosec B105
