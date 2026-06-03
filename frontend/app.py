import streamlit as st
from api_client import check_health, convert_images


st.set_page_config(page_title="Streamlit Frontend", layout="centered")

st.title("Image Converter")

# Check backend health
with st.sidebar:
    st.header("Status Sistem")
    health_status = check_health()
    if health_status:
        st.success("Backend terhubung")
    else:
        st.error("Backend tidak terhubung")

# Form Input
uploaded_files = st.file_uploader(
    "Unggah gambar...",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True
)

col1, col2 = st.columns(2)
with col1:
    target_format = st.selectbox("Pilih format target", ["jpg", "jpeg", "png", "webp"])
with col2:
    quality = st.slider("Kualitas (%)", min_value=1, max_value=100, value=80)

# Convert Button
if st.button("Konversi", type="primary"):
    if not uploaded_files:
        st.warning("Silakan unggah setidaknya satu gambar.")
    else:
        with st.spinner("Mengonversi gambar..."):
            zip_result = convert_images(uploaded_files, target_format, quality)
            
            if zip_result:
                st.success("Gambar berhasil dikonversi!")
                st.download_button(
                    label="Unduh Hasil Konversi (ZIP)",
                    data=zip_result,
                    file_name="converted_images.zip",
                    mime="application/zip"
                )
