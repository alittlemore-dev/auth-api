from asyncio import IncompleteReadError
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientConnectionError, ClientSession

from infra.config.constants import constants
from infra.http.telegram_status_client import HttpTelegramBotStatusClient

TEST_CREDENTIAL = "test-service-secret"


@pytest.mark.parametrize(
    ("body", "ready"),
    [
        (b'{"status":"ready"}', True),
        (b'{"status":"disabled"}', False),
        (b'{"status":"connecting"}', False),
        (b'{"status":"failed"}', False),
        (b'{"status":"unknown"}', False),
        (b"[]", False),
        (b'{"status":true}', False),
        (b"not-json", False),
        (b"\xff", False),
    ],
)
async def test_status_response_fails_closed(body: bytes, ready: bool) -> None:
    session = MagicMock(spec=ClientSession)
    response = session.get.return_value.__aenter__.return_value
    response.status = 200
    response.content.readexactly = AsyncMock(side_effect=IncompleteReadError(body, 1025))
    client = HttpTelegramBotStatusClient(
        session=session,
        status_url="http://bot.test/status",
        service_secret=TEST_CREDENTIAL,
        available=True,
    )

    assert await client.is_ready() is ready
    kwargs = session.get.call_args.kwargs
    assert kwargs["headers"] == {"X-Telegram-Service-Secret": "test-service-secret"}
    assert kwargs["allow_redirects"] is False
    assert kwargs["auto_decompress"] is False
    assert kwargs["timeout"].total == constants.telegram.status_timeout_seconds
    response.content.readexactly.assert_awaited_once_with(
        constants.telegram.max_status_response_bytes + 1,
    )


@pytest.mark.parametrize("status", [301, 401, 403, 404, 500, 503])
async def test_failed_http_status_is_unready(status: int) -> None:
    session = MagicMock(spec=ClientSession)
    response = session.get.return_value.__aenter__.return_value
    response.status = status
    client = HttpTelegramBotStatusClient(
        session=session,
        status_url="http://bot.test/status",
        service_secret=TEST_CREDENTIAL,
        available=True,
    )

    assert not await client.is_ready()
    response.content.readexactly.assert_not_called()


@pytest.mark.parametrize("error", [ClientConnectionError("private-origin"), TimeoutError()])
async def test_transport_failure_is_unready(error: Exception) -> None:
    session = MagicMock(spec=ClientSession)
    session.get.side_effect = error
    client = HttpTelegramBotStatusClient(
        session=session,
        status_url="http://bot.test/status",
        service_secret=TEST_CREDENTIAL,
        available=True,
    )

    assert not await client.is_ready()
    assert "test-service-secret" not in repr(client)
    assert "bot.test" not in repr(client)


async def test_oversized_response_is_unready() -> None:
    session = MagicMock(spec=ClientSession)
    response = session.get.return_value.__aenter__.return_value
    response.status = 200
    response.content.readexactly = AsyncMock(return_value=b"x" * 1025)
    client = HttpTelegramBotStatusClient(
        session=session,
        status_url="http://bot.test/status",
        service_secret=TEST_CREDENTIAL,
        available=True,
    )

    assert not await client.is_ready()


@pytest.mark.parametrize(("available", "secret"), [(False, "test-secret"), (True, "")])
async def test_disabled_or_missing_credential_never_requests_status(
    available: bool,
    secret: str,
) -> None:
    session = MagicMock(spec=ClientSession)
    client = HttpTelegramBotStatusClient(
        session=session,
        status_url="http://bot.test/status",
        service_secret=secret,
        available=available,
    )

    assert not await client.is_ready()
    session.get.assert_not_called()
