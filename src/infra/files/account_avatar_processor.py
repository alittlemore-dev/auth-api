import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from core.account.avatar_schemas import AccountAvatarUpload, ProcessedAccountAvatar
from core.account.clients import AccountAvatarProcessor
from core.account.exceptions import InvalidAccountAvatarError
from infra.config.constants import constants

FORMAT_MIME_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class PillowAccountAvatarProcessor(AccountAvatarProcessor):
    def process(self, *, upload: AccountAvatarUpload) -> ProcessedAccountAvatar:
        self._validate_upload(upload=upload)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                normalized = self._normalize(upload=upload)
        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            OSError,
            SyntaxError,
            UnidentifiedImageError,
            ValueError,
        ) as error:
            raise InvalidAccountAvatarError from error
        return ProcessedAccountAvatar(content=normalized.getvalue())

    @staticmethod
    def _validate_upload(*, upload: AccountAvatarUpload) -> None:
        avatar = constants.account_avatar
        if not upload.content or len(upload.content) > avatar.max_source_bytes:
            raise InvalidAccountAvatarError
        if upload.declared_mime_type.lower() not in avatar.supported_mime_types:
            raise InvalidAccountAvatarError

    @staticmethod
    def _normalize(*, upload: AccountAvatarUpload) -> BytesIO:
        with Image.open(BytesIO(upload.content)) as source:
            detected_mime_type = FORMAT_MIME_TYPES.get(source.format or "")
            if detected_mime_type != upload.declared_mime_type.lower():
                raise InvalidAccountAvatarError
            if getattr(source, "is_animated", False) or getattr(source, "n_frames", 1) != 1:
                raise InvalidAccountAvatarError
            if source.width * source.height > constants.account_avatar.max_decoded_pixels:
                raise InvalidAccountAvatarError

            oriented = ImageOps.exif_transpose(source)
            oriented.load()
            normalized_mode = (
                "RGBA"
                if oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info
                else "RGB"
            )
            converted = oriented.convert(normalized_mode)
            side = min(converted.size)
            left = (converted.width - side) // 2
            top = (converted.height - side) // 2
            cropped = converted.crop((left, top, left + side, top + side))
            resized = cropped.resize(
                (
                    constants.account_avatar.output_size_pixels,
                    constants.account_avatar.output_size_pixels,
                ),
                Image.Resampling.LANCZOS,
            )

            output = BytesIO()
            resized.save(
                output,
                format="WEBP",
                quality=constants.account_avatar.webp_quality,
                method=constants.account_avatar.webp_method,
            )
            return output
