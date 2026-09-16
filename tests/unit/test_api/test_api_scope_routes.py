import pytest
from httpx import codes

from tests.test_cases import ApiTestCase


class TestApiScopeRoutes(ApiTestCase):
    @pytest.mark.parametrize(
        ("path", "expected_status"),
        [
            ("/api/auth/healthcheck", codes.OK),
            ("/api/auth/account/base", codes.OK),
            ("/api/auth/admin/accounts", codes.UNAUTHORIZED),
            ("/api/auth/docs", codes.OK),
        ],
    )
    def test_auth_service_routes_use_public_namespace(
        self,
        path: str,
        expected_status: int,
    ) -> None:
        response = self.no_auth_api.client.get(path)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "path",
        [
            "/api/healthcheck",
            "/api/account/base",
            "/api/admin/accounts",
            "/api/docs",
        ],
    )
    def test_legacy_root_routes_are_not_served(self, path: str) -> None:
        response = self.no_auth_api.client.get(path)
        assert response.status_code == codes.NOT_FOUND

    @pytest.mark.parametrize(
        "path",
        [
            "/api/auth/articles",
            "/api/auth/competency-matrix/items",
            "/api/auth/contacts",
            "/api/auth/admin/files",
            "/api/auth/admin/agent-clients",
            "/api/auth/admin/tools/cache",
            "/api/auth/i18n/languages",
            "/sitemap.xml",
            "/internal/agent/v1/matrix/authoring-context",
        ],
    )
    def test_product_routes_are_not_served(self, path: str) -> None:
        response = self.no_auth_api.client.get(path)
        assert response.status_code == codes.NOT_FOUND
