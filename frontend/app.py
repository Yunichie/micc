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

_DEFAULTS: dict = {
    "s_preset":      "Custom",
    "s_mode":        "Kualitas",
    "s_format":      "jpeg",
    "s_quality":     80,
    "s_target_kb":   200,
    "s_resize":      False,
    "s_max_dim":     1920,
    "s_grayscale":   False,
    "s_strip_exif":  False,
    "s_auto_rotate": True,
    "r_result_bytes":  None,
    "r_stats":         None,
    "r_is_single":     False,
    "r_use_size_mode": False,
    "r_format":        "jpeg",
    "c_health":        None,
    "_applied_preset": None,
}

for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

PRESETS: dict[str, dict | None] = {
    "Custom": None,
    "🌐  Web (WEBP · 80% · max 1920px)": {
        "s_format": "webp",  "s_mode": "Kualitas",          "s_quality": 80,
        "s_resize": True,    "s_max_dim": 1920,
        "s_grayscale": False, "s_strip_exif": True,          "s_auto_rotate": True,
    },
    "📧  Email (JPEG · max 300 KB)": {
        "s_format": "jpeg",  "s_mode": "Target Ukuran File", "s_target_kb": 300,
        "s_resize": True,    "s_max_dim": 1600,
        "s_grayscale": False, "s_strip_exif": True,          "s_auto_rotate": True,
    },
    "🖼️  Thumbnail (JPEG · 70% · max 400px)": {
        "s_format": "jpeg",  "s_mode": "Kualitas",           "s_quality": 70,
        "s_resize": True,    "s_max_dim": 400,
        "s_grayscale": False, "s_strip_exif": True,           "s_auto_rotate": True,
    },
    "🖨️  Print (PNG · max compression)": {
        "s_format": "png",   "s_mode": "Kualitas",           "s_quality": 100,
        "s_resize": False,   "s_max_dim": None,
        "s_grayscale": False, "s_strip_exif": False,          "s_auto_rotate": True,
    },
    "⬛  Grayscale (JPEG · 85%)": {
        "s_format": "jpeg",  "s_mode": "Kualitas",           "s_quality": 85,
        "s_resize": False,   "s_max_dim": None,
        "s_grayscale": True,  "s_strip_exif": False,          "s_auto_rotate": True,
    },
}

def _apply_preset(name: str) -> None:
    cfg = PRESETS.get(name)
    if cfg is None:
        return
    for k, v in cfg.items():
        if v is not None:
            st.session_state[k] = v

@st.cache_data(ttl=60, show_spinner=False)
def _cached_health() -> bool:
    return check_health() is not None

@st.cache_data(show_spinner=False)
def _image_info(file_bytes: bytes, filename: str) -> tuple[int, int, float]:
    """Return (width, height, size_kb) without keeping the Image object."""
    img = Image.open(io.BytesIO(file_bytes))
    return img.width, img.height, len(file_bytes) / 1024

@st.cache_data(show_spinner=False)
def _open_image(file_bytes: bytes) -> Image.Image:
    """Decode image bytes once; result is cached for the session."""
    return Image.open(io.BytesIO(file_bytes))

st.title("Image Converter and Optimizer")
st.write("Unggah gambar Anda, pilih format dan kualitas, lalu konversi dengan mudah!")

st.selectbox("Preset", list(PRESETS.keys()), key="s_preset")

if st.session_state["s_preset"] != st.session_state["_applied_preset"]:
    _apply_preset(st.session_state["s_preset"])
    st.session_state["_applied_preset"] = st.session_state["s_preset"]

uploaded_files = st.file_uploader(
    "Unggah gambar...",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
)

if uploaded_files:
    with st.expander(f"Preview ({len(uploaded_files)} gambar diunggah)", expanded=True):
        cols = st.columns(min(len(uploaded_files), 4))
        for i, f in enumerate(uploaded_files):
            raw = f.getvalue()
            w, h, kb = _image_info(raw, f.name)
            with cols[i % 4]:
                st.image(raw, use_container_width=True)
                st.caption(f"{f.name}\n{w}×{h}px · {kb:.1f} KB")

st.markdown("---")

st.radio(
    "Mode konversi",
    ["Kualitas", "Target Ukuran File"],
    horizontal=True,
    key="s_mode",
    help=(
        "**Kualitas**: atur kualitas kompresi secara langsung.\n\n"
        "**Target Ukuran File**: backend mencari kualitas terbaik "
        "yang menghasilkan file ≤ ukuran yang Anda tentukan."
    ),
)
use_size_mode = st.session_state["s_mode"] == "Target Ukuran File"

col1, col2 = st.columns(2)

with col1:
    st.selectbox("Format target", ["jpeg", "png", "webp", "jpg"], key="s_format")

with col2:
    is_png = st.session_state["s_format"] == "png"

    if use_size_mode:
        st.number_input(
            "Ukuran target (KB)",
            min_value=1, step=10,
            key="s_target_kb",
            help=(
                "Backend akan mencari kualitas tertinggi yang menghasilkan "
                "file ≤ nilai ini. Jika tidak tercapai, hasil terkecil yang "
                "mungkin akan dikembalikan."
            ),
        )
    elif is_png:
        st.slider(
            "Tingkat kompresi PNG",
            min_value=1, max_value=100,
            key="s_quality",
            help=(
                "PNG bersifat lossless. Nilai ini mengontrol tingkat kompresi "
                "(bukan kualitas visual). Lebih tinggi = file lebih kecil, "
                "encoding lebih lambat."
            ),
        )
    else:
        st.slider(
            "Kualitas (%)",
            min_value=1, max_value=100,
            key="s_quality",
            help=(
                "Untuk WEBP: nilai < 75 memberi penghematan besar; "
                "di atas 90 perbedaan visual hampir tidak terlihat. "
                "Untuk JPEG: 80–85 adalah titik manis kualitas/ukuran."
            ),
        )

st.markdown("Opsi tambahan")

st.checkbox("Batasi dimensi maksimal", key="s_resize")
if st.session_state["s_resize"]:
    st.number_input(
        "Dimensi maksimal (px)",
        min_value=16, step=1,
        key="s_max_dim",
    )

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.checkbox("Grayscale", key="s_grayscale")
with col_b:
    st.checkbox(
        "Hapus EXIF", key="s_strip_exif",
        help="Menghapus metadata seperti lokasi GPS, model kamera, dan tanggal.",
    )
with col_c:
    st.checkbox(
        "Auto-rotate", key="s_auto_rotate",
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
        ss = st.session_state
        max_dim = int(ss["s_max_dim"]) if ss["s_resize"] else None

        with st.spinner("Mengonversi gambar..."):
            if use_size_mode:
                result_bytes, stats = convert_images_to_size(
                    uploaded_files,
                    target_format=ss["s_format"],
                    target_size_kb=int(ss["s_target_kb"]),
                    max_dimension=max_dim,
                    grayscale=ss["s_grayscale"],
                    strip_exif=ss["s_strip_exif"],
                    auto_rotate=ss["s_auto_rotate"],
                )
            else:
                result_bytes, stats = convert_images(
                    uploaded_files,
                    target_format=ss["s_format"],
                    quality=int(ss["s_quality"]),
                    max_dimension=max_dim,
                    grayscale=ss["s_grayscale"],
                    strip_exif=ss["s_strip_exif"],
                    auto_rotate=ss["s_auto_rotate"],
                )

        if result_bytes and stats:
            st.session_state["r_result_bytes"]  = result_bytes
            st.session_state["r_stats"]         = stats
            st.session_state["r_is_single"]     = len(uploaded_files) == 1
            st.session_state["r_use_size_mode"] = use_size_mode
            st.session_state["r_format"]        = ss["s_format"]

if st.session_state["r_result_bytes"] is not None:
    result_bytes  = st.session_state["r_result_bytes"]
    stats         = st.session_state["r_stats"]
    is_single     = st.session_state["r_is_single"]
    result_format = st.session_state["r_format"]
    was_size_mode = st.session_state["r_use_size_mode"]

    st.success("Gambar berhasil dikonversi!")

    if is_single:
        fname = stats[0]["filename"]
        mime_map = {
            "jpeg": "image/jpeg", "jpg": "image/jpeg",
            "png": "image/png",   "webp": "image/webp",
        }
        st.download_button(
            label=f"Unduh {fname}",
            data=result_bytes,
            file_name=fname,
            mime=mime_map.get(result_format.lower(), "application/octet-stream"),
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

    if was_size_mode:
        missed = [s for s in stats if s.get("target_missed")]
        if missed:
            names = ", ".join(s["filename"] for s in missed)
            st.warning(
                f"Ukuran target tidak tercapai untuk: **{names}**. "
                "File dikembalikan dengan kualitas minimum yang tersedia."
            )

    if uploaded_files:
        st.markdown("### Sebelum vs Sesudah")

        if is_single:
            converted_map = {stats[0]["filename"]: result_bytes}
        else:
            converted_map = {}
            with zipfile.ZipFile(io.BytesIO(result_bytes)) as zf:
                for name in zf.namelist():
                    converted_map[name] = zf.read(name)

        for stat, orig_file in zip(stats, uploaded_files):
            orig_bytes = orig_file.getvalue()
            conv_bytes = converted_map.get(stat["filename"])

            orig_kb   = stat["original_size"] / 1024
            conv_kb   = stat["compressed_size"] / 1024
            reduction = (1 - stat["compressed_size"] / stat["original_size"]) * 100

            st.markdown(f"**{stat['filename']}**")
            left, right = st.columns(2)

            with left:
                orig_img = _open_image(orig_bytes)
                st.image(orig_img, use_container_width=True)
                st.caption(
                    f"Asli · {orig_img.width}×{orig_img.height}px · {orig_kb:.1f} KB"
                )

            with right:
                if conv_bytes:
                    conv_img = _open_image(conv_bytes)
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
        df["Ukuran Asli"]  = (df["original_size"]   / 1024).round(2).astype(str) + " KB"
        df["Ukuran Hasil"] = (df["compressed_size"]  / 1024).round(2).astype(str) + " KB"
        df["Pengurangan"]  = (
            (1 - df["compressed_size"] / df["original_size"]) * 100
        ).round(2).astype(str) + " %"

        cols_show = ["filename", "Ukuran Asli", "Ukuran Hasil", "Pengurangan"]
        if was_size_mode:
            df["Target Tercapai"] = df["target_missed"].apply(
                lambda x: "❌" if x else "✅"
            )
            cols_show.append("Target Tercapai")

        df_display = df[cols_show].copy()
        df_display.columns = (
            ["Nama File", "Ukuran Asli", "Ukuran Hasil", "Pengurangan"]
            + (["Target Tercapai"] if was_size_mode else [])
        )
        st.dataframe(df_display, use_container_width=True, hide_index=True)
