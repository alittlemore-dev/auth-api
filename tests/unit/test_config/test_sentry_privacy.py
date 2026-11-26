from unittest.mock import patch

import pytest
from sentry_sdk import Client

from infra.config.initializers import init_sentry
from infra.config.settings import settings


def test_sentry_does_not_export_auth_request_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings.sentry, "use", True)
    with patch("infra.config.initializers.sentry_sdk.init") as initialize:
        init_sentry()
    options = initialize.call_args.kwargs
    with Client(
        **{**options, "dsn": "", "default_integrations": False, "spotlight": False},
    ) as client:
        assert not client.should_send_default_pii()
    assert options["include_local_variables"] is False
    assert options["max_request_body_size"] == "never"
    for callback_name in ("before_send", "before_send_transaction"):
        event = {
            "request": {
                "url": "https://auth.example/api/auth/refresh",
                "cookies": {"__Secure-msid": "test-session-secret"},
                "data": {"password": "test-password"},
                "headers": {"Authorization": "Bearer test-access-token"},
            },
        }
        result = options[callback_name](event, {})
        assert result["request"] == {"url": "https://auth.example/api/auth/refresh"}
