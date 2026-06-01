import streamlit as st
import httpx

# Configuration
BACKEND_URL = "http://localhost:8000"
st.set_page_config(page_title="Streamlit Frontend", layout="centered")

st.title("Hello, world!")

if st.button("Check Backend Health"):
    try:
        response = httpx.get(f"{BACKEND_URL}/api/health")
        response.raise_for_status()

        data = response.json()
        st.success(f"Status: {data['status']}")
        st.info(f"Message: {data['message']}")

    except httpx.RequestError as e:
        st.error(f"Failed to connect to backend: {e}")
