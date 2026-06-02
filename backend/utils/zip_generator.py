import io
import zipfile
from typing import List, Tuple

def create_zip_buffer(files: List[Tuple[str, bytes]]) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in files:
            zf.writestr(filename, data)

    zip_buffer.seek(0)
    return zip_buffer

def iter_file(buffer: io.BytesIO, chunk_size: int = 65536):
    try:
        while True:
            chunk = buffer.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        buffer.close()
