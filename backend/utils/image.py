import asyncio
import io
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Tuple

from PIL import Image, ImageOps

from backend.core.config import settings

_pool: Optional[ProcessPoolExecutor] = None


def init_pool() -> None:
    global _pool
    _pool = ProcessPoolExecutor(max_workers=settings.MAX_WORKERS)


def shutdown_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=True)
        _pool = None


def _prepare_image(
    img: Image.Image,
    pil_format: str,
    max_dimension: Optional[int],
    grayscale: bool,
    auto_rotate: bool,
) -> Image.Image:
    if auto_rotate:
        img = ImageOps.exif_transpose(img)

    if max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    if pil_format in ("JPEG", "WEBP"):
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

    if grayscale and img.mode not in ("L", "LA"):
        if img.mode != "RGB":
            img = img.convert("RGB")
        img = img.convert("L")

    return img


def _build_save_kwargs(
    img: Image.Image,
    pil_format: str,
    quality: int,
    strip_exif: bool,
) -> dict:
    save_kwargs: dict = {"format": pil_format}

    if pil_format in ("JPEG", "WEBP"):
        save_kwargs["quality"] = quality
        if not strip_exif and hasattr(img, "info") and "exif" in img.info:
            save_kwargs["exif"] = img.info["exif"]

    elif pil_format == "PNG":
        save_kwargs["optimize"] = True
        save_kwargs["compress_level"] = round((quality - 1) / 99 * 9)

    return save_kwargs


def compress_image_sync(
    file_bytes: bytes,
    output_format: str,
    quality: int,
    max_dimension: Optional[int] = None,
    grayscale: bool = False,
    strip_exif: bool = False,
    auto_rotate: bool = True,
) -> Tuple[bytes, str, int, int]:
    original_size = len(file_bytes)
    pil_format = output_format.upper()
    if pil_format == "JPG":
        pil_format = "JPEG"

    with io.BytesIO(file_bytes) as input_buffer:
        with Image.open(input_buffer) as img:
            img = _prepare_image(img, pil_format, max_dimension, grayscale, auto_rotate)
            save_kwargs = _build_save_kwargs(img, pil_format, quality, strip_exif)
            output_buffer = io.BytesIO()
            img.save(output_buffer, **save_kwargs)
            ext = "jpg" if pil_format == "JPEG" else pil_format.lower()
            compressed_bytes = output_buffer.getvalue()
            return compressed_bytes, ext, original_size, len(compressed_bytes)


def compress_to_size_sync(
    file_bytes: bytes,
    output_format: str,
    target_size_kb: int,
    max_dimension: Optional[int] = None,
    grayscale: bool = False,
    strip_exif: bool = False,
    auto_rotate: bool = True,
) -> Tuple[bytes, str, int, int]:
    original_size = len(file_bytes)
    pil_format = output_format.upper()
    if pil_format == "JPG":
        pil_format = "JPEG"

    target_bytes = target_size_kb * 1024

    with io.BytesIO(file_bytes) as input_buffer:
        with Image.open(input_buffer) as img:
            img = _prepare_image(img, pil_format, max_dimension, grayscale, auto_rotate)

            lo, hi = 1, 100
            best_bytes: Optional[bytes] = None

            for _ in range(8):
                if lo > hi:
                    break
                mid = (lo + hi) // 2
                save_kwargs = _build_save_kwargs(img, pil_format, mid, strip_exif)
                buf = io.BytesIO()
                img.save(buf, **save_kwargs)
                candidate = buf.getvalue()

                if len(candidate) <= target_bytes:
                    best_bytes = candidate
                    lo = mid + 1
                else:
                    hi = mid - 1

            # Fallback: return minimum-quality result if target was unreachable.
            if best_bytes is None:
                save_kwargs = _build_save_kwargs(img, pil_format, 1, strip_exif)
                buf = io.BytesIO()
                img.save(buf, **save_kwargs)
                best_bytes = buf.getvalue()

            ext = "jpg" if pil_format == "JPEG" else pil_format.lower()
            return best_bytes, ext, original_size, len(best_bytes)


async def process_image(
    file_bytes: bytes,
    output_format: str,
    quality: int,
    max_dimension: Optional[int] = None,
    grayscale: bool = False,
    strip_exif: bool = False,
    auto_rotate: bool = True,
) -> Tuple[bytes, str, int, int]:
    if _pool is None:
        raise RuntimeError(
            "Image process pool is not initialised. "
            "Ensure the FastAPI lifespan handler has started."
        )
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
        auto_rotate,
    )


async def process_image_to_size(
    file_bytes: bytes,
    output_format: str,
    target_size_kb: int,
    max_dimension: Optional[int] = None,
    grayscale: bool = False,
    strip_exif: bool = False,
    auto_rotate: bool = True,
) -> Tuple[bytes, str, int, int]:
    if _pool is None:
        raise RuntimeError(
            "Image process pool is not initialised. "
            "Ensure the FastAPI lifespan handler has started."
        )
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _pool,
        compress_to_size_sync,
        file_bytes,
        output_format,
        target_size_kb,
        max_dimension,
        grayscale,
        strip_exif,
        auto_rotate,
    )
