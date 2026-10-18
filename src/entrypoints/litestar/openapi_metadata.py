from dataclasses import dataclass
from functools import cache
from typing import cast

from litestar import Litestar
from litestar._openapi.plugin import OpenAPIPlugin
from litestar.openapi.spec import (
    Example,
    OpenAPI,
    OpenAPIMediaType,
    OpenAPIResponse,
    Operation,
    Reference,
    RequestBody,
    Schema,
)
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.params import BodyKwarg
from litestar.routes.http import HTTPRoute
from verbose_http_exceptions import error_by_status_mapping

from entrypoints.litestar.api.openapi import JSONExample


@dataclass(frozen=True)
class RequestBodyMetadata:
    description: str
    examples: dict[str, Example]


@cache
def install_openapi_request_body_metadata() -> None:
    build_openapi = OpenAPIPlugin._build_openapi  # noqa: SLF001

    def build_openapi_with_request_body_metadata(plugin: OpenAPIPlugin) -> OpenAPI:
        openapi_schema = build_openapi(plugin)
        apply_openapi_request_body_metadata(app=plugin.app, openapi_schema=openapi_schema)
        apply_error_schema_metadata(openapi_schema=openapi_schema)
        return openapi_schema

    setattr(  # noqa: B010
        OpenAPIPlugin,
        "_build_openapi",
        build_openapi_with_request_body_metadata,
    )


def apply_openapi_request_body_metadata(
    *,
    app: Litestar,
    openapi_schema: OpenAPI,
) -> None:
    if openapi_schema.paths is None:
        return

    for route in app.routes:
        if not isinstance(route, HTTPRoute) or route.path_format is None:
            continue
        path_item = openapi_schema.paths.get(route.path_format)
        if path_item is None:
            continue
        for route_handler in route.route_handlers:
            data_field = route_handler.parsed_fn_signature.parameters.get("data")
            metadata = (
                build_request_body_metadata(body_kwarg=data_field.kwarg_definition)
                if data_field is not None and isinstance(data_field.kwarg_definition, BodyKwarg)
                else None
            )
            for method in route_handler.http_methods:
                operation = cast("Operation | None", getattr(path_item, method.lower()))
                if operation is None:
                    continue
                apply_generated_error_metadata(operation=operation)
                if metadata is not None:
                    apply_request_body_metadata(operation=operation, metadata=metadata)
                if route_handler.content_encoding == "binary" and operation.responses:
                    response = operation.responses.get(str(route_handler.status_code))
                    apply_binary_response_metadata(response=response)


def build_request_body_metadata(body_kwarg: BodyKwarg) -> RequestBodyMetadata | None:
    if body_kwarg.description is None or body_kwarg.examples is None:
        return None
    return RequestBodyMetadata(
        description=body_kwarg.description,
        examples=format_request_body_examples(examples=body_kwarg.examples),
    )


def format_request_body_examples(*, examples: list[Example]) -> dict[str, Example]:
    return {
        example.id or f"example{index}": example for index, example in enumerate(examples, start=1)
    }


def apply_request_body_metadata(
    *,
    operation: Operation,
    metadata: RequestBodyMetadata,
) -> None:
    if not isinstance(operation.request_body, RequestBody):
        return

    request_body = operation.request_body
    if request_body.description is None:
        request_body.description = metadata.description
    for media_type_schema in request_body.content.values():
        if media_type_schema.examples is None:
            media_type_schema.examples = dict(metadata.examples)


def apply_binary_response_metadata(*, response: OpenAPIResponse | Reference | None) -> None:
    if not isinstance(response, OpenAPIResponse) or not response.content:
        return
    # Litestar creates an untyped Stream schema; preserve the binary HTTP contract.
    for media_type, media_schema in response.content.items():
        media_schema.schema = Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.BINARY,
            content_media_type=media_type,
        )


def apply_generated_error_metadata(*, operation: Operation) -> None:
    for status_code, response in (operation.responses or {}).items():
        if status_code != "400" or not isinstance(response, OpenAPIResponse):
            continue
        if not response.content:
            continue
        content = response.content.get("application/json")
        if content is None or not isinstance(content.schema, Schema):
            continue
        # Automatically generated validation responses ignore the installed exception handler.
        response.content = {
            "application/json": OpenAPIMediaType(
                schema=Reference(ref="#/components/schemas/VerboseHTTPExceptionDict"),
                examples={
                    "validation": JSONExample(value=error_by_status_mapping[400]().as_dict())
                },
            ),
        }
        response.description = (
            "Invalid request path, query or body; validation errors return HTTP 400."
        )


def apply_error_schema_metadata(*, openapi_schema: OpenAPI) -> None:
    if openapi_schema.components is None or not openapi_schema.components.schemas:
        return
    schema = openapi_schema.components.schemas.get("VerboseHTTPExceptionDict")
    if not isinstance(schema, Schema) or schema.properties is None:
        return
    metadata: dict[str, tuple[str, list[object]]] = {
        "code": (
            "Broad error category: client_error, server_error or validation_error.",
            ["validation_error"],
        ),
        "type": ("Specific error kind; validation kinds follow the input validator.", ["missing"]),
        "message": ("Human-readable explanation of this failure.", ["Field required"]),
        "location": (
            "Input source such as body, query or path; null when not tied to an input.",
            ["query", None],
        ),
        "attr": (
            "Field or parameter associated with the failure; null when not applicable.",
            ["page", None],
        ),
        "nested_errors": (
            "Multiple validation failures, recursively nested; absent for a single failure.",
            [],
        ),
    }
    for name, (description, examples) in metadata.items():
        property_schema = schema.properties.get(name)
        if isinstance(property_schema, Schema):
            property_schema.description = description
            if examples:
                property_schema.examples = examples
