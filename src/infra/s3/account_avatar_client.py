from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus

from botocore.exceptions import BotoCoreError, ClientError
from types_aiobotocore_s3.client import S3Client
from types_aiobotocore_s3.type_defs import ListObjectsV2OutputTypeDef

from core.account.clients import AccountAvatarClient
from core.account.exceptions import AccountAvatarStorageError
from infra.config.loggers import log_sanitized_exception


@dataclass(frozen=True, slots=True, kw_only=True)
class S3AccountAvatarClient(AccountAvatarClient):
    client: S3Client
    bucket_name: str
    stream_chunk_size: int

    async def upload(self, *, object_name: str, content: bytes) -> None:
        try:
            await self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=content,
                ContentType="image/webp",
            )
        except (BotoCoreError, ClientError) as error:
            self._raise_storage_error(event="Account avatar upload failed", error=error)

    async def stream(self, *, object_name: str) -> AsyncIterator[bytes]:
        try:
            response = await self.client.get_object(
                Bucket=self.bucket_name,
                Key=object_name,
            )
        except (BotoCoreError, ClientError) as error:
            self._raise_storage_error(event="Account avatar read failed", error=error)
        body = response["Body"]
        try:
            while chunk := await body.read(self.stream_chunk_size):
                yield chunk
        except (BotoCoreError, ClientError) as error:
            self._raise_storage_error(event="Account avatar stream failed", error=error)
        finally:
            body.close()

    async def delete(self, *, object_name: str) -> None:
        try:
            await self.client.delete_object(
                Bucket=self.bucket_name,
                Key=object_name,
            )
        except ClientError as error:
            if self._is_not_found(error=error):
                return
            self._raise_storage_error(event="Account avatar delete failed", error=error)
        except BotoCoreError as error:
            self._raise_storage_error(event="Account avatar delete failed", error=error)

    async def list_objects_older_than(self, *, cutoff: datetime) -> tuple[str, ...]:
        object_names: list[str] = []
        continuation_token: str | None = None
        try:
            while True:
                response = await self._list_page(continuation_token=continuation_token)
                for item in response.get("Contents", []):
                    key = item.get("Key")
                    last_modified = item.get("LastModified")
                    if key is not None and last_modified is not None and last_modified < cutoff:
                        object_names.append(key)
                if not response.get("IsTruncated"):
                    break
                continuation_token = response.get("NextContinuationToken")
                if continuation_token is None:
                    break
        except (BotoCoreError, ClientError) as error:
            self._raise_storage_error(event="Account avatar listing failed", error=error)
        return tuple(object_names)

    async def _list_page(
        self,
        *,
        continuation_token: str | None,
    ) -> ListObjectsV2OutputTypeDef:
        if continuation_token is None:
            return await self.client.list_objects_v2(Bucket=self.bucket_name)
        return await self.client.list_objects_v2(
            Bucket=self.bucket_name,
            ContinuationToken=continuation_token,
        )

    @staticmethod
    def _is_not_found(*, error: ClientError) -> bool:
        error_matches = False
        status_matches = False
        with suppress(KeyError):
            error_matches = str(error.response["Error"]["Code"]) in {
                "404",
                "NoSuchKey",
                "NotFound",
            }
        with suppress(KeyError):
            status_matches = (
                error.response["ResponseMetadata"]["HTTPStatusCode"] == HTTPStatus.NOT_FOUND
            )
        return error_matches or status_matches

    @staticmethod
    def _raise_storage_error(*, event: str, error: Exception) -> None:
        log_sanitized_exception(event=event, error=error)
        raise AccountAvatarStorageError from error
