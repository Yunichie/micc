import os
import io
import asyncio
from typing import List
from fastapi import UploadFile

from backend.utils.image import process_image
from backend.utils.zip_generator import create_zip_buffer

async def process_multiple_images(
    files: List[UploadFile],
    output_format: str,
    quality: int
) -> io.BytesIO:
    tasks = []
    filenames = []

    for file in files:
        safe_filename = file.filename or "image"
        file_bytes = await file.read()
        base_name, _ = os.path.splitext(safe_filename)
        filenames.append(base_name)
        tasks.append(process_image(file_bytes, output_format, quality))

    results = await asyncio.gather(*tasks)

    processed_files = []
    seen_names = set()
    for i, (processed_bytes, ext) in enumerate(results):
        base = filenames[i]
        new_filename = f"{base}.{ext}"

        counter = 1
        while new_filename in seen_names:
            new_filename = f"{base}_{counter}.{ext}"
            counter += 1

        seen_names.add(new_filename)
        processed_files.append((new_filename, processed_bytes))

    loop = asyncio.get_running_loop()
    zip_buffer = await loop.run_in_executor(None, create_zip_buffer, processed_files)

    return zip_buffer
