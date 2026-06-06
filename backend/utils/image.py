import asyncio
import io
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Tuple

from PIL import Image

from backend.core.config import settings

# Process pool for CPU bound image compression
_pool = ProcessPoolExecutor(max_workers=settings.MAX_WORKERS)


def compress_image_sync(
    file_bytes: bytes,
    output_format: str,
    quality: int,
    max_dimension: Optional[int] = None,
    grayscale: bool = False,
    strip_exif: bool = False,
) -> Tuple[bytes, str, int, int]:
    original_size = len(file_bytes)

    with io.BytesIO(file_bytes) as input_buffer:
        with Image.open(input_buffer) as img:
            if max_dimension and max(img.width, img.height) > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

            if grayscale:
                img = img.convert("L")

            if output_format.upper() in ["JPEG", "JPG"] and img.mode in (
                "RGBA",
                "P",
                "LA",
            ):
                img = img.convert("RGB")
            elif output_format.upper() in ["JPEG", "JPG"] and img.mode == "L":
                pass

            output_buffer = io.BytesIO()
            pil_format = output_format.upper()
            if pil_format == "JPG":
                pil_format = "JPEG"

            save_kwargs = {"format": pil_format}

            if strip_exif:
                pass

            if pil_format in ["JPEG", "WEBP"]:
                save_kwargs["quality"] = quality
                if not strip_exif and hasattr(img, "info") and "exif" in img.info:
                    save_kwargs["exif"] = img.info["exif"]
            elif pil_format == "PNG":
                save_kwargs["optimize"] = True

            img.save(output_buffer, **save_kwargs)

            ext = "jpg" if pil_format == "JPEG" else pil_format.lower()
            compressed_bytes = output_buffer.getvalue()
            return compressed_bytes, ext, original_size, len(compressed_bytes)


async def process_image(
    file_bytes: bytes,
    output_format: str,
    quality: int,
    max_dimension: Optional[int] = None,
    grayscale: bool = False,
    strip_exif: bool = False,
) -> Tuple[bytes, str, int, int]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _pool,
        compress_image_sync,
        file_bytes,
        output_format,
        quality,
        max_dimension,
        grayscale,
        strip_exif,
    )
