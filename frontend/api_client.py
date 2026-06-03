import httpx
import streamlit as st

BACKEND_URL = "http://localhost:8000/api/v1"

def check_health():
    try:
        response = httpx.get("http://localhost:8000/health")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        return None

def convert_images(uploaded_files, target_format, quality):
    url = f"{BACKEND_URL}/convert"

    files_payload = []
    for file in uploaded_files:
        files_payload.append(('files', (file.name, file.getvalue(), file.type)))
    
    data_payload = {
        "format": target_format,
        "quality": quality
    }

    try:
        response = httpx.post(url, files=files_payload, data=data_payload, timeout=60.0)
        response.raise_for_status()

        return response.content
    except httpx.RequestError as e:
        st.error(f"An error occurred while connecting to the backend: {e}")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"Backend returned an error: {e.response.text}")
        return None