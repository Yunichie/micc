import streamlit as st
import pandas as pd
from api_client import check_health, convert_images


st.set_page_config(page_title="Streamlit Frontend", layout="centered")

st.title("Image Converter and Optimizer")
st.write("Unggah gambar Anda, pilih format dan kualitas, lalu konversi dengan mudah!")

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

# Additional Optimization Options
st.markdown("Optimasi tambahan")

enable_resize = st.checkbox("Ubah Ukuran Maksimal Gambar")
max_dimension = None
if enable_resize:
    max_dimension = st.number_input("Dimensi Maksimal (px)", min_value=16, value=1080, step=1)

col_opt1, col_opt2 = st.columns(2)
with col_opt1:
    grayscale = st.checkbox("Konversi ke Grayscale")
with col_opt2:
    strip_exif = st.checkbox("Hapus Metadata EXIF")


# Convert Button
if st.button("Konversi", type="primary"):
    if not uploaded_files:
        st.warning("Silakan unggah setidaknya satu gambar.")
    else:
        with st.spinner("Mengonversi gambar..."):
            zip_result, stats = convert_images(uploaded_files, target_format, quality, max_dimension, grayscale, strip_exif)
            
            if zip_result:
                st.success("Gambar berhasil dikonversi!")

                st.download_button(
                    label="Unduh Hasil (ZIP)",
                    data=zip_result,
                    file_name="optimized_images.zip",
                    mime="application/zip"
                )

                # Display conversion stats if available
                if stats:
                    with st.expander("Lihat Statistik Konversi"):
                        df = pd.DataFrame(stats)

                        df["Original Size (KB)"] = (df["original_size"] / 1024).round(2).astype(str) + " KB"
                        df["Optimized Size (KB)"] = (df["compressed_size"] / 1024).round(2).astype(str) + " KB"

                        # Rasio Efisiensi Ukuran File
                        df["Size Reduction"] = (
                            (1 - (df["compressed_size"] / df["original_size"])) * 100
                        ).round(2).astype(str) + " %"

                        df_display = df[["filename", "Original Size (KB)", "Optimized Size (KB)", "Size Reduction"]]
                        df_display.columns = ["Nama File", "Ukuran Asli", "Ukuran Optimasi", "Pengurangan Ukuran"]

                        st.dataframe(df_display, use_container_width=True, hide_index=True)