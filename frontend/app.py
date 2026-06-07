import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import streamlit as st
from PIL import Image

from api_client import check_health, convert_images, convert_images_to_size

st.set_page_config(page_title="Micc — Image Converter", layout="centered")

st.title("Image Converter and Optimizer")
st.write("Unggah gambar Anda, pilih format dan kualitas, lalu konversi dengan mudah!")

with st.sidebar:
    st.header("Status Sistem")
    if check_health():
        st.success("Backend terhubung")
    else:
        st.error("Backend tidak terhubung")

PRESETS = {
    "Custom": None,
    "🌐  Web (WEBP · 80% · max 1920px)": {
        "format": "webp", "mode": "quality", "quality": 80,
        "resize": True, "max_dim": 1920,
        "grayscale": False, "strip_exif": True, "auto_rotate": True,
    },
    "📧  Email (JPEG · max 300 KB)": {
        "format": "jpeg", "mode": "size", "target_kb": 300,
        "resize": True, "max_dim": 1600,
        "grayscale": False, "strip_exif": True, "auto_rotate": True,
    },
    "🖼️  Thumbnail (JPEG · 70% · max 400px)": {
        "format": "jpeg", "mode": "quality", "quality": 70,
        "resize": True, "max_dim": 400,
        "grayscale": False, "strip_exif": True, "auto_rotate": True,
    },
    "🖨️  Print (PNG · max compression)": {
        "format": "png", "mode": "quality", "quality": 100,
        "resize": False, "max_dim": None,
        "grayscale": False, "strip_exif": False, "auto_rotate": True,
    },
    "⬛  Grayscale (JPEG · 85%)": {
        "format": "jpeg", "mode": "quality", "quality": 85,
        "resize": False, "max_dim": None,
        "grayscale": True, "strip_exif": False, "auto_rotate": True,
    },
}

selected_preset_name = st.selectbox("Preset", list(PRESETS.keys()))
preset = PRESETS[selected_preset_name]

def _default(key, fallback):
    if preset is not None and key in preset:
        return preset[key]
    return st.session_state.get(key, fallback)

uploaded_files = st.file_uploader(
    "Unggah gambar...",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
)

if uploaded_files:
    with st.expander(f"Preview ({len(uploaded_files)} gambar diunggah)", expanded=True):
        cols = st.columns(min(len(uploaded_files), 4))
        for i, f in enumerate(uploaded_files):
            with cols[i % 4]:
                img = Image.open(f)
                size_kb = len(f.getvalue()) / 1024
                st.image(img, use_container_width=True)
                st.caption(
                    f"{f.name}\n{img.width}×{img.height}px · {size_kb:.1f} KB"
                )
                f.seek(0)  # reset after Image.open consumed the buffer

st.markdown("---")

mode = st.radio(
    "Mode konversi",
    ["Kualitas", "Target Ukuran File"],
    index=0 if _default("mode", "quality") == "quality" else 1,
    horizontal=True,
    help=(
        "**Kualitas**: atur kualitas kompresi secara langsung.\n\n"
        "**Target Ukuran File**: backend mencari kualitas terbaik "
        "yang menghasilkan file ≤ ukuran yang Anda tentukan."
    ),
)
use_size_mode = mode == "Target Ukuran File"

col1, col2 = st.columns(2)

with col1:
    fmt_options = ["jpeg", "png", "webp", "jpg"]
    preset_fmt = _default("format", "jpeg")
    fmt_index = fmt_options.index(preset_fmt) if preset_fmt in fmt_options else 0
    target_format = st.selectbox("Format target", fmt_options, index=fmt_index)

with col2:
    is_png = target_format.lower() == "png"

    if use_size_mode:
        target_kb = st.number_input(
            "Ukuran target (KB)",
            min_value=1,
            value=int(_default("target_kb", 200)),
            step=10,
            help=(
                "Backend akan mencari kualitas tertinggi yang menghasilkan "
                "file ≤ nilai ini. Jika tidak tercapai, hasil terkecil yang "
                "mungkin akan dikembalikan."
            ),
        )
        quality = 80  # unused in this mode but keeps the signature consistent
    elif is_png:
        quality = st.slider(
            "Tingkat kompresi PNG",
            min_value=1, max_value=100,
            value=int(_default("quality", 50)),
            help=(
                "PNG bersifat lossless. Nilai ini mengontrol tingkat kompresi "
                "(bukan kualitas visual). Lebih tinggi = file lebih kecil, "
                "encoding lebih lambat."
            ),
        )
        target_kb = 200  # unused
    else:
        quality = st.slider(
            "Kualitas (%)",
            min_value=1, max_value=100,
            value=int(_default("quality", 80)),
            help=(
                "Untuk WEBP: nilai < 75 memberi penghematan besar; "
                "di atas 90 perbedaan visual hampir tidak terlihat. "
                "Untuk JPEG: 80–85 adalah titik manis kualitas/ukuran."
            ),
        )
        target_kb = 200  # unused

st.markdown("Opsi tambahan")

enable_resize = st.checkbox(
    "Batasi dimensi maksimal",
    value=bool(_default("resize", False)),
)
max_dimension = None
if enable_resize:
    max_dimension = st.number_input(
        "Dimensi maksimal (px)",
        min_value=16,
        value=int(_default("max_dim", 1920) or 1920),
        step=1,
    )

col_a, col_b, col_c = st.columns(3)
with col_a:
    grayscale = st.checkbox("Grayscale", value=bool(_default("grayscale", False)))
with col_b:
    strip_exif = st.checkbox(
        "Hapus EXIF",
        value=bool(_default("strip_exif", False)),
        help="Menghapus metadata seperti lokasi GPS, model kamera, dan tanggal.",
    )
with col_c:
    auto_rotate = st.checkbox(
        "Auto-rotate",
        value=bool(_default("auto_rotate", True)),
        help=(
            "Koreksi orientasi foto dari tag EXIF secara otomatis. "
            "Direkomendasikan untuk foto dari ponsel."
        ),
    )

st.markdown("---")

if st.button("Konversi", type="primary", use_container_width=True):
    if not uploaded_files:
        st.warning("Silakan unggah setidaknya satu gambar.")
    else:
        # Persist settings to session_state so they survive re-runs.
        st.session_state.update({
            "mode": "size" if use_size_mode else "quality",
            "format": target_format,
            "quality": quality,
            "target_kb": target_kb,
            "resize": enable_resize,
            "max_dim": max_dimension,
            "grayscale": grayscale,
            "strip_exif": strip_exif,
            "auto_rotate": auto_rotate,
        })

        with st.spinner("Mengonversi gambar..."):
            if use_size_mode:
                result_bytes, stats = convert_images_to_size(
                    uploaded_files, target_format, target_kb,
                    max_dimension, grayscale, strip_exif, auto_rotate,
                )
            else:
                result_bytes, stats = convert_images(
                    uploaded_files, target_format, quality,
                    max_dimension, grayscale, strip_exif, auto_rotate,
                )

        if result_bytes and stats:
            st.success("Gambar berhasil dikonversi!")

            is_single = len(uploaded_files) == 1
            if is_single:
                fname = stats[0]["filename"]
                mime_map = {
                    "jpeg": "image/jpeg", "jpg": "image/jpeg",
                    "png": "image/png", "webp": "image/webp",
                }
                mime = mime_map.get(target_format.lower(), "application/octet-stream")
                st.download_button(
                    label=f"Unduh {fname}",
                    data=result_bytes,
                    file_name=fname,
                    mime=mime,
                    use_container_width=True,
                )
            else:
                st.download_button(
                    label="Unduh Semua (ZIP)",
                    data=result_bytes,
                    file_name="optimized_images.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

            if use_size_mode:
                missed = [s for s in stats if s.get("target_missed")]
                if missed:
                    names = ", ".join(s["filename"] for s in missed)
                    st.warning(
                        f"Ukuran target tidak tercapai untuk: **{names}**. "
                        "File dikembalikan dengan kualitas minimum yang tersedia."
                    )

            st.markdown("### Sebelum vs Sesudah")

            original_map = {f.name: f.getvalue() for f in uploaded_files}

            if is_single:
                converted_images_map = {stats[0]["filename"]: result_bytes}
            else:
                converted_images_map = {}
                with zipfile.ZipFile(io.BytesIO(result_bytes)) as zf:
                    for name in zf.namelist():
                        converted_images_map[name] = zf.read(name)

            for stat, orig_file in zip(stats, uploaded_files):
                orig_bytes = orig_file.getvalue()
                conv_bytes = converted_images_map.get(stat["filename"])

                orig_kb = stat["original_size"] / 1024
                conv_kb = stat["compressed_size"] / 1024
                reduction = (1 - stat["compressed_size"] / stat["original_size"]) * 100

                st.markdown(f"**{stat['filename']}**")
                left, right = st.columns(2)

                with left:
                    orig_img = Image.open(io.BytesIO(orig_bytes))
                    st.image(orig_img, use_container_width=True)
                    st.caption(
                        f"Asli · {orig_img.width}×{orig_img.height}px · {orig_kb:.1f} KB"
                    )

                with right:
                    if conv_bytes:
                        conv_img = Image.open(io.BytesIO(conv_bytes))
                        st.image(conv_img, use_container_width=True)

                        reduction_str = (
                            f"▼ {reduction:.1f}%" if reduction >= 0
                            else f"▲ {abs(reduction):.1f}%"
                        )
                        st.caption(
                            f"Hasil · {conv_img.width}×{conv_img.height}px · "
                            f"{conv_kb:.1f} KB · {reduction_str}"
                        )

            with st.expander("Lihat tabel statistik"):
                df = pd.DataFrame(stats)
                df["Ukuran Asli"] = (df["original_size"] / 1024).round(2).astype(str) + " KB"
                df["Ukuran Hasil"] = (df["compressed_size"] / 1024).round(2).astype(str) + " KB"
                df["Pengurangan"] = (
                    (1 - df["compressed_size"] / df["original_size"]) * 100
                ).round(2).astype(str) + " %"
                cols_show = ["filename", "Ukuran Asli", "Ukuran Hasil", "Pengurangan"]
                if use_size_mode:
                    df["Target Tercapai"] = df["target_missed"].apply(
                        lambda x: "❌" if x else "✅"
                    )
                    cols_show.append("Target Tercapai")
                df_display = df[cols_show].copy()
                df_display.columns = (
                    ["Nama File", "Ukuran Asli", "Ukuran Hasil", "Pengurangan"]
                    + (["Target Tercapai"] if use_size_mode else [])
                )
                st.dataframe(df_display, use_container_width=True, hide_index=True)
