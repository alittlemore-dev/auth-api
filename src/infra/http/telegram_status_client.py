import json
from asyncio import IncompleteReadError
from dataclasses import dataclass, field
from http import HTTPStatus

from aiohttp import ClientError, ClientSession, ClientTimeout

from core.account.clients import TelegramBotStatusClient
from infra.config.constants import constants


@dataclass(frozen=True, slots=True, kw_only=True)
class HttpTelegramBotStatusClient(TelegramBotStatusClient):
    session: ClientSession
    status_url: str = field(repr=False)
    service_secret: str = field(repr=False)
    available: bool

    async def is_ready(self) -> bool:
        if not self.available or not self.service_secret:
            return False
        headers: dict[str, str] = {
            constants.telegram.service_auth_header: self.service_secret,
        }
        try:
            async with self.session.get(
                self.status_url,
                headers=headers,
                timeout=ClientTimeout(total=constants.telegram.status_timeout_seconds),
                allow_redirects=False,
                auto_decompress=False,
            ) as response:
                if response.status != HTTPStatus.OK:
                    return False
                try:
                    await response.content.readexactly(
                        constants.telegram.max_status_response_bytes + 1,
                    )
                except IncompleteReadError as exc:
                    content = exc.partial
                else:
                    return False
                payload: object = json.loads(content)
                return payload == {"status": "ready"}
        except ClientError, TimeoutError, ValueError:
            return False
