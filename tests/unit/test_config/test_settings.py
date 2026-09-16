from collections.abc import Generator

import pytest

from infra.config.settings import Settings


class TestSettings:
    @pytest.fixture(autouse=True)
    def setup(self, test_settings: Settings) -> Generator[None]:
        self.settings = test_settings
        orig = self.settings.app.domain
        orig_debug = self.settings.app.debug
        self.settings.app.domain = "alittlemoron.ru"
        self.settings.app.url_schema = "https"
        self.settings.app.debug = False
        yield
        self.settings.app.domain = orig
        self.settings.app.debug = orig_debug
        self.settings.app.url_schema = "http"

    def test_app_base_url(self) -> None:
        assert self.settings.app.base_url == "https://alittlemoron.ru"

    def test_app_base_url_adds_debug_port_for_local_domain(self) -> None:
        self.settings.app.domain = "localhost"
        self.settings.app.debug = True
        assert self.settings.app.base_url == "https://localhost:8000"

    def test_app_public_origin_ignores_debug_port(self) -> None:
        self.settings.app.debug = True
        assert self.settings.app.public_origin == "https://alittlemoron.ru"

    def test_app_get_url(self) -> None:
        assert (
            self.settings.app.get_url(path="/sitemap.xml") == "https://alittlemoron.ru/sitemap.xml"
        )

    def test_valkey_get_url(self) -> None:
        self.settings.valkey.host = "localhost"
        self.settings.valkey.port = 6379
        assert self.settings.valkey.get_url(db=0).get_secret_value() == "valkey://localhost:6379/0"
