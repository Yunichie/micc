import json
from typing import Optional

import httpx
import streamlit as st

BACKEND_URL = "http://localhost:8000/api/v1"


def check_health():
    try:
        response = httpx.get("http://localhost:8000/health")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError:
        return None


def _parse_response(response: httpx.Response):
    """Return (content_bytes, stats_list) from any conversion response."""
    stats = None
    stats_header = response.headers.get("X-Conversion-Stats")
    if stats_header:
        stats = json.loads(stats_header)
    return response.content, stats


def convert_images(
    uploaded_files,
    target_format: str,
    quality: int,
    max_dimension: Optional[int] = None,
    grayscale: bool = False,
    strip_exif: bool = False,
    auto_rotate: bool = True,
):
    """Quality-based conversion. Returns (bytes, stats)."""
    files_payload = [
        ("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files
    ]
    data_payload = {
        "format": target_format,
        "quality": quality,
        "grayscale": grayscale,
        "strip_exif": strip_exif,
        "auto_rotate": auto_rotate,
    }
    if max_dimension is not None:
        data_payload["max_dimension"] = max_dimension

    try:
        response = httpx.post(
            f"{BACKEND_URL}/convert",
            files=files_payload,
            data=data_payload,
            timeout=60.0,
        )
        response.raise_for_status()
        return _parse_response(response)
    except httpx.RequestError as e:
        st.error(f"An error occurred while connecting to the backend: {e}")
        return None, None
    except httpx.HTTPStatusError as e:
        st.error(f"Backend returned an error: {e.response.text}")
        return None, None


def convert_images_to_size(
    uploaded_files,
    target_format: str,
    target_size_kb: int,
    max_dimension: Optional[int] = None,
    grayscale: bool = False,
    strip_exif: bool = False,
    auto_rotate: bool = True,
):
    """Target-size-based conversion. Returns (bytes, stats)."""
    files_payload = [
        ("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files
    ]
    data_payload = {
        "format": target_format,
        "target_size_kb": target_size_kb,
        "grayscale": grayscale,
        "strip_exif": strip_exif,
        "auto_rotate": auto_rotate,
    }
    if max_dimension is not None:
        data_payload["max_dimension"] = max_dimension

    try:
        response = httpx.post(
            f"{BACKEND_URL}/convert-to-size",
            files=files_payload,
            data=data_payload,
            timeout=60.0,
        )
        response.raise_for_status()
        return _parse_response(response)
    except httpx.RequestError as e:
        st.error(f"An error occurred while connecting to the backend: {e}")
        return None, None
    except httpx.HTTPStatusError as e:
        st.error(f"Backend returned an error: {e.response.text}")
        return None, None
