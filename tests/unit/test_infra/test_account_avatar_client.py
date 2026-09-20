from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from botocore.exceptions import ClientError

from core.account.exceptions import AccountAvatarStorageError
from infra.s3.account_avatar_client import S3AccountAvatarClient


class FakeStreamingBody:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.closed = False

    async def read(self, _size: int) -> bytes:
        return self.chunks.pop(0) if self.chunks else b""

    def close(self) -> None:
        self.closed = True


def client_error(*, code: str, status: int = 500) -> ClientError:
    return ClientError(
        {
            "Error": {"Code": code, "Message": "storage failed"},
            "ResponseMetadata": {"HTTPStatusCode": status},
        },
        "operation",
    )


class TestS3AccountAvatarClient:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.s3 = AsyncMock()
        self.client = S3AccountAvatarClient(
            client=self.s3,
            bucket_name="auth-avatars",
            stream_chunk_size=4,
        )

    async def test_uploads_to_private_bucket_without_public_configuration(self) -> None:
        await self.client.upload(object_name="avatars/new.webp", content=b"image")

        self.s3.put_object.assert_awaited_once_with(
            Bucket="auth-avatars",
            Key="avatars/new.webp",
            Body=b"image",
            ContentType="image/webp",
        )
        assert not hasattr(self.client, "create_bucket_policy")
        assert not hasattr(self.client, "create_bucket_cors")
        assert not hasattr(self.client, "presign")

    async def test_streams_in_chunks_and_closes_body(self) -> None:
        body = FakeStreamingBody([b"abcd", b"ef"])
        self.s3.get_object.return_value = {"Body": body}

        chunks = [chunk async for chunk in self.client.stream(object_name="avatars/a.webp")]

        assert chunks == [b"abcd", b"ef"]
        assert body.closed is True

    async def test_delete_is_idempotent_for_missing_object(self) -> None:
        self.s3.delete_object.side_effect = client_error(code="NoSuchKey", status=404)

        await self.client.delete(object_name="avatars/missing.webp")

    async def test_lists_paginated_objects_older_than_cutoff(self) -> None:
        cutoff = datetime(2026, 9, 20, tzinfo=UTC)
        self.s3.list_objects_v2.side_effect = [
            {
                "Contents": [
                    {"Key": "avatars/old.webp", "LastModified": cutoff - timedelta(seconds=1)},
                    {"Key": "avatars/new.webp", "LastModified": cutoff},
                ],
                "IsTruncated": True,
                "NextContinuationToken": "next",
            },
            {
                "Contents": [
                    {"Key": "avatars/older.webp", "LastModified": cutoff - timedelta(days=1)},
                ],
                "IsTruncated": False,
            },
        ]

        result = await self.client.list_objects_older_than(cutoff=cutoff)

        assert result == ("avatars/old.webp", "avatars/older.webp")
        assert self.s3.list_objects_v2.await_count == 2

    async def test_storage_error_is_sanitized(self) -> None:
        self.s3.put_object.side_effect = client_error(code="InternalError")

        with pytest.raises(
            AccountAvatarStorageError, match="Avatar storage operation failed"
        ) as error:
            await self.client.upload(object_name="avatars/private-name.webp", content=b"private")

        assert "private-name" not in str(error.value)
        assert "private" not in str(error.value)
