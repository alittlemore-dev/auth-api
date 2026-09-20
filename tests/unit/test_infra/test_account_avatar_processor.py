from io import BytesIO

import pytest
from PIL import Image, PngImagePlugin

from core.account.avatar_schemas import AccountAvatarUpload
from core.account.exceptions import InvalidAccountAvatarError
from infra.config.constants import constants
from infra.files.account_avatar_processor import PillowAccountAvatarProcessor


def encode_image(
    image: Image.Image,
    *,
    image_format: str,
    **kwargs: object,
) -> bytes:
    output = BytesIO()
    image.save(output, format=image_format, **kwargs)
    return output.getvalue()


def open_processed(content: bytes) -> Image.Image:
    image = Image.open(BytesIO(content))
    image.load()
    return image


class TestPillowAccountAvatarProcessor:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.processor = PillowAccountAvatarProcessor()

    @pytest.mark.parametrize(
        ("size", "bands"),
        [
            ((900, 300), ((0, 300), (300, 600), (600, 900))),
            ((300, 900), ((0, 300), (300, 600), (600, 900))),
        ],
    )
    def test_center_crops_landscape_and_portrait_images(
        self,
        size: tuple[int, int],
        bands: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
    ) -> None:
        image = Image.new("RGB", size)
        colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255))
        for (start, end), color in zip(bands, colors, strict=True):
            if size[0] > size[1]:
                image.paste(color, (start, 0, end, size[1]))
            else:
                image.paste(color, (0, start, size[0], end))

        result = self.processor.process(
            upload=AccountAvatarUpload(
                content=encode_image(image, image_format="PNG"),
                declared_mime_type="image/png",
            ),
        )

        processed = open_processed(result.content)
        assert result.mime_type == "image/webp"
        assert processed.size == (512, 512)
        assert processed.format == "WEBP"
        assert getattr(processed, "n_frames", 1) == 1
        center_pixel = processed.convert("RGB").getpixel((256, 256))
        assert isinstance(center_pixel, tuple)
        red, green, blue = center_pixel
        assert green > 240
        assert red < 20
        assert blue < 20

    def test_applies_exif_orientation_before_cropping(self) -> None:
        image = Image.new("RGB", (300, 600), (255, 0, 0))
        image.paste((0, 255, 0), (0, 150, 300, 450))
        exif = Image.Exif()
        exif[274] = 6

        result = self.processor.process(
            upload=AccountAvatarUpload(
                content=encode_image(image, image_format="JPEG", exif=exif),
                declared_mime_type="image/jpeg",
            ),
        )

        processed = open_processed(result.content)
        center_pixel = processed.convert("RGB").getpixel((256, 256))
        assert isinstance(center_pixel, tuple)
        red, green, blue = center_pixel
        assert green > red
        assert green > blue
        assert "exif" not in processed.info

    def test_preserves_transparency_and_drops_source_metadata(self) -> None:
        image = Image.new("RGBA", (600, 400), (20, 40, 60, 0))
        image.paste((20, 40, 60, 255), (200, 100, 400, 300))
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Description", "private source metadata")

        result = self.processor.process(
            upload=AccountAvatarUpload(
                content=encode_image(image, image_format="PNG", pnginfo=metadata),
                declared_mime_type="image/png",
            ),
        )

        processed = open_processed(result.content)
        assert processed.mode == "RGBA"
        corner_pixel = processed.getpixel((0, 0))
        center_pixel = processed.getpixel((256, 256))
        assert isinstance(corner_pixel, tuple)
        assert isinstance(center_pixel, tuple)
        assert corner_pixel[3] == 0
        assert center_pixel[3] > 240
        assert "Description" not in processed.info
        assert "exif" not in processed.info
        assert "icc_profile" not in processed.info

    @pytest.mark.parametrize(
        ("content", "declared_mime_type"),
        [
            (b"", "image/png"),
            (b"not-an-image", "image/png"),
        ],
    )
    def test_rejects_invalid_content_with_sanitized_error(
        self,
        content: bytes,
        declared_mime_type: str,
    ) -> None:
        with pytest.raises(InvalidAccountAvatarError, match="Invalid account avatar") as error:
            self.processor.process(
                upload=AccountAvatarUpload(
                    content=content,
                    declared_mime_type=declared_mime_type,
                ),
            )

        assert "not-an-image" not in str(error.value)

    def test_rejects_source_larger_than_five_mebibytes(self) -> None:
        with pytest.raises(InvalidAccountAvatarError, match="Invalid account avatar"):
            self.processor.process(
                upload=AccountAvatarUpload(
                    content=b"x" * (5 * 1024 * 1024 + 1),
                    declared_mime_type="image/png",
                ),
            )

    def test_rejects_declared_and_detected_mime_mismatch(self) -> None:
        content = encode_image(Image.new("RGB", (10, 10)), image_format="JPEG")

        with pytest.raises(InvalidAccountAvatarError, match="Invalid account avatar"):
            self.processor.process(
                upload=AccountAvatarUpload(content=content, declared_mime_type="image/png"),
            )

    def test_rejects_gif(self) -> None:
        content = encode_image(Image.new("RGB", (10, 10)), image_format="GIF")

        with pytest.raises(InvalidAccountAvatarError, match="Invalid account avatar"):
            self.processor.process(
                upload=AccountAvatarUpload(content=content, declared_mime_type="image/gif"),
            )

    def test_rejects_animated_webp(self) -> None:
        frames = [Image.new("RGB", (10, 10), color) for color in ("red", "blue")]
        content = encode_image(
            frames[0],
            image_format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0,
        )

        with pytest.raises(InvalidAccountAvatarError, match="Invalid account avatar"):
            self.processor.process(
                upload=AccountAvatarUpload(content=content, declared_mime_type="image/webp"),
            )

    def test_rejects_excessive_decoded_dimensions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(constants.account_avatar, "max_decoded_pixels", 100)
        content = encode_image(Image.new("RGB", (11, 10)), image_format="PNG")

        with pytest.raises(InvalidAccountAvatarError, match="Invalid account avatar"):
            self.processor.process(
                upload=AccountAvatarUpload(content=content, declared_mime_type="image/png"),
            )
