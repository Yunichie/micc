import httpx
import streamlit as st
import json

BACKEND_URL = "http://localhost:8000/api/v1"

def check_health():
    try:
        response = httpx.get("http://localhost:8000/health")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError:
        return None

def convert_images(uploaded_files, target_format, quality, max_dimension=None, grayscale=False, strip_exif=False):
    url = f"{BACKEND_URL}/convert"

    files_payload = []
    for file in uploaded_files:
        files_payload.append(('files', (file.name, file.getvalue(), file.type)))
    
    data_payload = {
        "format": target_format,
        "quality": quality,
        "grayscale": grayscale,
        "strip_exif": strip_exif
    }

    if max_dimension is not None:
        data_payload["max_dimension"] = max_dimension

    try:
        response = httpx.post(url, files=files_payload, data=data_payload, timeout=60.0)
        response.raise_for_status()

        stats = None
        stats_header = response.headers.get("X-Conversion-Stats")
        if stats_header:
            stats = json.loads(stats_header)

        return response.content, stats
    
    except httpx.RequestError as e:
        st.error(f"An error occurred while connecting to the backend: {e}")
        return None, None
    except httpx.HTTPStatusError as e:
        st.error(f"Backend returned an error: {e.response.text}")
        return None, None