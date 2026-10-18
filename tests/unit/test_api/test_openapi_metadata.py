from collections.abc import Iterable, Mapping
from typing import Any

from litestar import Litestar
from litestar.testing import TestClient
from pydantic import BaseModel, TypeAdapter
from verbose_http_exceptions.exc.base import VerboseHTTPExceptionDict

from entrypoints.litestar.api.account.schemas import (
    AccountSettingsSchema,
    CurrentAccountUpdateRequestSchema,
)
from entrypoints.litestar.api.accounts.schemas import (
    ManagedAccountCreateRequestSchema,
    ManagedAccountPasswordUpdateRequestSchema,
    ManagedAccountRoleUpdateRequestSchema,
)
from entrypoints.litestar.api.api_tokens.schemas import ApiTokenCreateSchema, ApiTokenPasswordSchema
from entrypoints.litestar.api.auth.schemas import LoginRequestSchema


class TestOpenApiMetadata:
    def test_api_token_operation_descriptions_document_management_contract(
        self, app: Litestar
    ) -> None:
        paths = app.openapi_schema.to_schema()["paths"]
        base = "/api/auth/account/me/api-tokens"
        for path, method in (
            (base, "get"),
            (base, "post"),
            (base + "/permissions", "get"),
            (base + "/{token_id}/reveal", "post"),
            (base + "/{token_id}/revoke", "post"),
        ):
            description = paths[path][method]["description"]
            assert "Browser session only" in description
            assert "personal API tokens cannot manage API tokens" in description
            assert "no-store" in description
        assert "immutable" in paths[base]["post"]["description"]
        assert "current-password confirmation" in paths[base]["post"]["description"]
        reveal = paths[base + "/{token_id}/reveal"]["post"]["description"]
        assert "same active secret" in reveal
        assert "current-password confirmation" in reveal

    def test_account_time_zone_is_documented_as_iana_string(self, app: Litestar) -> None:
        schema = app.openapi_schema.to_schema()
        settings_schema = schema["components"]["schemas"]["AccountSettingsSchema"]
        time_zone_schema = settings_schema["properties"]["timeZone"]

        assert time_zone_schema["type"] == "string"
        assert time_zone_schema["format"] == "iana-time-zone"
        assert time_zone_schema["maxLength"] == 255
        assert "IANA" in time_zone_schema["description"]
        assert "Asia/Yerevan" in time_zone_schema["examples"]

    def test_openapi_documents_protected_admin_operations_and_permissions(
        self, app: Litestar
    ) -> None:
        schema = app.openapi_schema.to_schema()
        admin_paths = sorted(path for path in schema["paths"] if path.startswith("/api/auth/admin"))

        assert "/api/auth/admin/accounts" in admin_paths
        operation = schema["paths"]["/api/auth/admin/accounts"]["get"]
        assert "auth.accounts.read" in operation["description"]
        assert operation["security"] == [{"bearerAuth": []}]
        assert "/api/auth/login" in schema["paths"]

    def test_visible_parameters_include_descriptions_and_examples(self, app: Litestar) -> None:
        schema = app.openapi_schema.to_schema()
        missing_metadata = [
            f"{method.upper()} {path} parameter {parameter['in']}:{parameter['name']} "
            f"missing {', '.join(missing)}"
            for path, method, operation in self._iter_operations(schema=schema)
            for parameter in operation.get("parameters", ())
            if (missing := self._missing_parameter_metadata(parameter=parameter))
        ]

        assert missing_metadata == []

    def test_visible_request_bodies_include_descriptions_and_examples(self, app: Litestar) -> None:
        schema = app.openapi_schema.to_schema()
        missing_metadata = [
            f"{method.upper()} {path} request body missing {', '.join(missing)}"
            for path, method, operation in self._iter_operations(schema=schema)
            if (request_body := operation.get("requestBody")) is not None
            if (missing := self._missing_request_body_metadata(request_body=request_body))
        ]

        assert missing_metadata == []

    def test_avatar_download_documents_webp_binary(self, app: Litestar) -> None:
        schema = app.openapi_schema.to_schema()
        response = schema["paths"]["/api/auth/account/me/avatar"]["get"]["responses"]["200"]
        assert set(response["content"]) == {"image/webp"}
        assert response["content"]["image/webp"]["schema"]["type"] == "string"
        assert response["content"]["image/webp"]["schema"]["format"] == "binary"

    def test_pagination_is_required_and_bounded(self, app: Litestar, client: TestClient) -> None:
        schema = app.openapi_schema.to_schema()
        operation = schema["paths"]["/api/auth/admin/accounts"]["get"]
        parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
        for name in ("page", "pageSize"):
            assert parameters[name]["required"] is True
            assert "default" not in parameters[name]["schema"]
            assert parameters[name]["schema"]["minimum"] == 1
        assert parameters["pageSize"]["schema"]["maximum"] == 100
        response = client.get("/api/auth/admin/accounts")
        assert response.status_code == 400
        TypeAdapter(VerboseHTTPExceptionDict).validate_python(response.json())

    def test_documented_errors_match_runtime_envelope(self, app: Litestar) -> None:
        schema = app.openapi_schema.to_schema()
        error_schema = schema["components"]["schemas"]["VerboseHTTPExceptionDict"]
        assert set(error_schema["required"]) == {"code", "type", "message", "location", "attr"}
        assert "nested_errors" in error_schema["properties"]
        assert "nestedErrors" not in error_schema["properties"]
        for _, _, operation in self._iter_operations(schema=schema):
            for code, response in operation["responses"].items():
                if int(code) < 400:
                    continue
                content = response["content"]["application/json"]
                assert content["schema"] == {
                    "$ref": "#/components/schemas/VerboseHTTPExceptionDict"
                }
                for example in content["examples"].values():
                    TypeAdapter(VerboseHTTPExceptionDict).validate_python(example["value"])

    def test_json_body_examples_validate_against_request_models(self, app: Litestar) -> None:
        schema = app.openapi_schema.to_schema()
        models: dict[tuple[str, str], type[BaseModel]] = {
            ("/api/auth/login", "post"): LoginRequestSchema,
            ("/api/auth/account/me", "patch"): CurrentAccountUpdateRequestSchema,
            ("/api/auth/account/me/settings", "put"): AccountSettingsSchema,
            ("/api/auth/account/me/api-tokens", "post"): ApiTokenCreateSchema,
            ("/api/auth/account/me/api-tokens/{token_id}/reveal", "post"): ApiTokenPasswordSchema,
            ("/api/auth/admin/accounts", "post"): ManagedAccountCreateRequestSchema,
            (
                "/api/auth/admin/accounts/{username}/password",
                "put",
            ): ManagedAccountPasswordUpdateRequestSchema,
            (
                "/api/auth/admin/accounts/{username}/role",
                "put",
            ): ManagedAccountRoleUpdateRequestSchema,
        }
        for (path, method), model in models.items():
            content = schema["paths"][path][method]["requestBody"]["content"]["application/json"]
            for example in content["examples"].values():
                model.model_validate(example["value"])

    @staticmethod
    def _iter_operations(
        *,
        schema: Mapping[str, Any],
    ) -> Iterable[tuple[str, str, Mapping[str, Any]]]:
        for path, path_schema in schema["paths"].items():
            for method, operation in path_schema.items():
                if method in {"get", "post", "put", "patch", "delete"}:
                    yield path, method, operation

    @staticmethod
    def _missing_parameter_metadata(*, parameter: Mapping[str, Any]) -> list[str]:
        missing: list[str] = []
        if not parameter.get("description"):
            missing.append("description")
        parameter_schema = parameter.get("schema", {})
        if "examples" not in parameter_schema and "examples" not in parameter:
            missing.append("examples")
        return missing

    @staticmethod
    def _missing_request_body_metadata(*, request_body: Mapping[str, Any]) -> list[str]:
        missing: list[str] = []
        if not request_body.get("description"):
            missing.append("description")
        content = request_body.get("content", {})
        has_examples = any(
            "examples" in media_schema or "examples" in media_schema.get("schema", {})
            for media_schema in content.values()
        )
        if not has_examples:
            missing.append("examples")
        return missing
