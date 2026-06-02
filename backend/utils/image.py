import io
import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Tuple
from PIL import Image

from backend.core.config import settings

# Process pool for CPU bound image compression
_pool = ProcessPoolExecutor(max_workers=settings.MAX_WORKERS)

def compress_image_sync(file_bytes: bytes, output_format: str, quality: int) -> Tuple[bytes, str]:
    with io.BytesIO(file_bytes) as input_buffer:
        with Image.open(input_buffer) as img:
            # Convert to RGB if saving as JPEG and image has Alpha
            if output_format.upper() in ["JPEG", "JPG"] and img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")

            output_buffer = io.BytesIO()
            pil_format = output_format.upper()
            if pil_format == "JPG":
                pil_format = "JPEG"

            save_kwargs = {"format": pil_format}
            if pil_format in ["JPEG", "WEBP"]:
                save_kwargs["quality"] = quality
            elif pil_format == "PNG":
                # PNG optimization
                save_kwargs["optimize"] = True

            img.save(output_buffer, **save_kwargs)

            ext = "jpg" if pil_format == "JPEG" else pil_format.lower()
            return output_buffer.getvalue(), ext

async def process_image(file_bytes: bytes, output_format: str, quality: int) -> Tuple[bytes, str]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _pool, compress_image_sync, file_bytes, output_format, quality
    )
