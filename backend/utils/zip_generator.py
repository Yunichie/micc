import io
import logging
import zipfile
from typing import Generator, List, Tuple

logger = logging.getLogger(__name__)


def create_zip_buffer(files: List[Tuple[str, bytes]]) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in files:
            zf.writestr(filename, data)

    zip_buffer.seek(0)
    return zip_buffer


def iter_file(buffer: io.BytesIO, chunk_size: int = 65536) -> Generator[bytes, None, None]:
    try:
        while True:
            chunk = buffer.read(chunk_size)
            if not chunk:
                break
            yield chunk
    except Exception as exc:
        logger.error("Error while streaming ZIP buffer: %s", exc, exc_info=True)
        raise
    finally:
        buffer.close()
