import json
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from backend.services.conversion import process_multiple_images
from backend.utils.zip_generator import iter_file

router = APIRouter()


@router.post("/convert")
async def convert_images(
    files: List[UploadFile] = File(...),
    format: str = Form("PNG"),
    quality: int = Form(80),
    max_dimension: Optional[int] = Form(None),
    grayscale: bool = Form(False),
    strip_exif: bool = Form(False),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    valid_formats = ["WEBP", "JPEG", "JPG", "PNG"]
    if format.upper() not in valid_formats:
        raise HTTPException(
            status_code=400, detail=f"Invalid format. Must be one of {valid_formats}"
        )

    if not (1 <= quality <= 100):
        raise HTTPException(status_code=400, detail="Quality must be between 1 and 100")

    if max_dimension is not None and max_dimension < 16:
        raise HTTPException(status_code=400, detail="max_dimension must be at least 16")

    try:
        zip_buffer, stats = await process_multiple_images(
            files, format, quality, max_dimension, grayscale, strip_exif
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing images: {str(e)}"
        )

    stats_json = json.dumps(stats)

    return StreamingResponse(
        iter_file(zip_buffer),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=optimized_images.zip",
            "X-Conversion-Stats": stats_json,
        },
    )
