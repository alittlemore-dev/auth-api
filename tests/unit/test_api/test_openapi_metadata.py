from collections.abc import Iterable, Mapping
from typing import Any

from litestar import Litestar


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
