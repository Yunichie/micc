import json
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse

from backend.services.conversion import (
    process_multiple_images,
    process_multiple_images_to_size,
)
from backend.utils.zip_generator import iter_file

router = APIRouter()

VALID_FORMATS = ["WEBP", "JPEG", "JPG", "PNG"]


def _validate_common(
    files: List[UploadFile],
    format: str,
    max_dimension: Optional[int],
) -> None:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if format.upper() not in VALID_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Must be one of {VALID_FORMATS}",
        )
    if max_dimension is not None and max_dimension < 16:
        raise HTTPException(status_code=400, detail="max_dimension must be at least 16")


def _stats_response(zip_buffer, stats, single: bool, fmt: str):
    """Return a direct file download for single images, ZIP for batches."""
    stats_json = json.dumps(stats)

    if single:
        import zipfile
        with zipfile.ZipFile(zip_buffer) as zf:
            name = zf.namelist()[0]
            data = zf.read(name)
        mime_map = {
            "JPEG": "image/jpeg", "JPG": "image/jpeg",
            "PNG": "image/png", "WEBP": "image/webp",
        }
        mime = mime_map.get(fmt.upper(), "application/octet-stream")
        return Response(
            content=data,
            media_type=mime,
            headers={
                "Content-Disposition": f'attachment; filename="{name}"',
                "X-Conversion-Stats": stats_json,
            },
        )

    return StreamingResponse(
        iter_file(zip_buffer),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=optimized_images.zip",
            "X-Conversion-Stats": stats_json,
        },
    )


@router.post("/convert")
async def convert_images(
    files: List[UploadFile] = File(...),
    format: str = Form("PNG"),
    quality: int = Form(80),
    max_dimension: Optional[int] = Form(None),
    grayscale: bool = Form(False),
    strip_exif: bool = Form(False),
    auto_rotate: bool = Form(True),
):
    _validate_common(files, format, max_dimension)

    if not (1 <= quality <= 100):
        raise HTTPException(status_code=400, detail="Quality must be between 1 and 100")

    try:
        zip_buffer, stats = await process_multiple_images(
            files, format, quality, max_dimension, grayscale, strip_exif, auto_rotate,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing images: {str(e)}")

    return _stats_response(zip_buffer, stats, single=len(files) == 1, fmt=format)


@router.post("/convert-to-size")
async def convert_images_to_size(
    files: List[UploadFile] = File(...),
    format: str = Form("JPEG"),
    target_size_kb: int = Form(200),
    max_dimension: Optional[int] = Form(None),
    grayscale: bool = Form(False),
    strip_exif: bool = Form(False),
    auto_rotate: bool = Form(True),
):
    _validate_common(files, format, max_dimension)

    if target_size_kb < 1:
        raise HTTPException(status_code=400, detail="target_size_kb must be at least 1")

    try:
        zip_buffer, stats = await process_multiple_images_to_size(
            files, format, target_size_kb, max_dimension, grayscale, strip_exif, auto_rotate,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing images: {str(e)}")

    # Flag any file that couldn't reach the target so the frontend can warn.
    target_bytes = target_size_kb * 1024
    for s in stats:
        s["target_missed"] = s["compressed_size"] > target_bytes

    return _stats_response(zip_buffer, stats, single=len(files) == 1, fmt=format)
