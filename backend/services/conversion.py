import asyncio
import io
import os
from typing import List, Optional

from fastapi import UploadFile

from backend.utils.image import process_image, process_image_to_size
from backend.utils.zip_generator import create_zip_buffer


def _build_zip_and_stats(
    filenames: list[str],
    results: list[tuple],
) -> tuple[io.BytesIO, list[dict]]:
    processed_files = []
    stats = []
    seen_names: set[str] = set()

    for i, (processed_bytes, ext, original_size, compressed_size) in enumerate(results):
        base = filenames[i]
        new_filename = f"{base}.{ext}"
        counter = 1
        while new_filename in seen_names:
            new_filename = f"{base}_{counter}.{ext}"
            counter += 1
        seen_names.add(new_filename)
        processed_files.append((new_filename, processed_bytes))
        stats.append(
            {
                "filename": new_filename,
                "original_size": original_size,
                "compressed_size": compressed_size,
            }
        )

    return create_zip_buffer(processed_files), stats


async def process_multiple_images(
    files: List[UploadFile],
    output_format: str,
    quality: int,
    max_dimension: Optional[int] = None,
    grayscale: bool = False,
    strip_exif: bool = False,
    auto_rotate: bool = True,
) -> tuple[io.BytesIO, list[dict]]:
    tasks = []
    filenames = []

    for file in files:
        safe_filename = file.filename or "image"
        file_bytes = await file.read()
        base_name, _ = os.path.splitext(safe_filename)
        filenames.append(base_name)
        tasks.append(
            process_image(
                file_bytes, output_format, quality, max_dimension,
                grayscale, strip_exif, auto_rotate,
            )
        )

    results = await asyncio.gather(*tasks)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _build_zip_and_stats, filenames, list(results)
    )


async def process_multiple_images_to_size(
    files: List[UploadFile],
    output_format: str,
    target_size_kb: int,
    max_dimension: Optional[int] = None,
    grayscale: bool = False,
    strip_exif: bool = False,
    auto_rotate: bool = True,
) -> tuple[io.BytesIO, list[dict]]:
    tasks = []
    filenames = []

    for file in files:
        safe_filename = file.filename or "image"
        file_bytes = await file.read()
        base_name, _ = os.path.splitext(safe_filename)
        filenames.append(base_name)
        tasks.append(
            process_image_to_size(
                file_bytes, output_format, target_size_kb, max_dimension,
                grayscale, strip_exif, auto_rotate,
            )
        )

    results = await asyncio.gather(*tasks)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _build_zip_and_stats, filenames, list(results)
    )
