#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import time
from datetime import datetime, date
from typing import Optional
import requests
import pandas as pd
import streamlit as st
import scrapetube
from io import BytesIO

# Enrichment wajib untuk tanggal pasti (recommended)
try:
    from yt_dlp import YoutubeDL
    YTDLP_AVAILABLE = True
except Exception:
    YTDLP_AVAILABLE = False

# ========= Helpers =========
def extract_text(node, keys=("simpleText", "text")):
    if not node:
        return None
    if isinstance(node, dict):
        for k in keys:
            if k in node and isinstance(node[k], str):
                return node[k]
        if "runs" in node and isinstance(node["runs"], list) and node["runs"]:
            return "".join([r.get("text", "") for r in node["runs"]])
    return None

def safe_get(d, path, default=None):
    cur = d
    try:
        for p in path:
            if isinstance(p, int):
                cur = cur[p]
            else:
                cur = cur.get(p, {})
        return cur if cur not in ({}, []) else default
    except Exception:
        return default

def build_thumb_url(video_id, quality="hq"):
    fname = {
        "mq": "mqdefault.jpg",
        "hq": "hqdefault.jpg",
        "sd": "sddefault.jpg",
        "maxres": "maxresdefault.jpg",
    }.get(quality, "hqdefault.jpg")
    return f"https://i.ytimg.com/vi/{video_id}/{fname}"

def ytdlp_fetch(video_url: str) -> dict:
    """
    Ambil metadata pasti (upload_date YYYYMMDD, description, like_count) via yt_dlp.
    Return dict minimal: {"published_date": "YYYY-MM-DD", "description": str|None, "like_count": int|None}
    """
    if not YTDLP_AVAILABLE:
        return {"published_date": None, "description": None, "like_count": None}
    try:
        ydl_opts = {"quiet": True, "skip_download": True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        up = info.get("upload_date")  # 'YYYYMMDD'
        pub_date = f"{up[0:4]}-{up[4:6]}-{up[6:8]}" if up else None
        return {
            "published_date": pub_date,
            "description": info.get("description"),
            "like_count": info.get("like_count"),
        }
    except Exception:
        return {"published_date": None, "description": None, "like_count": None}

def parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def in_date_range(pub: Optional[str], start_d: Optional[date], end_d: Optional[date]) -> bool:
    if not start_d and not end_d:
        return True
    if not pub:
        return False
    p = parse_date(pub)
    if not p:
        return False
    if start_d and p < start_d:
        return False
    if end_d and p > end_d:
        return False
    return True

def create_excel_with_images(df: pd.DataFrame, img_col="thumbnail_url", max_img_width=160) -> bytes:
    """
    Buat file Excel (bytes) dengan thumbnail di-embed.
    """
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from PIL import Image

    wb = Workbook()
    ws = wb.active
    ws.title = "videos"

    cols = df.columns.tolist()
    if img_col in cols:
        ordered_cols = [img_col] + [c for c in cols if c != img_col]
    else:
        ordered_cols = cols

    ws.append(ordered_cols)
    ws.column_dimensions["A"].width = 25 if ordered_cols and ordered_cols[0] == img_col else 20

    img_positions = []
    for i, row in df.reset_index(drop=True).iterrows():
        vals = [row.get(c, None) for c in ordered_cols]
        ws.append(vals)
        excel_row = i + 2  # header di baris 1
        if img_col in ordered_cols:
            col_idx = ordered_cols.index(img_col) + 1
            img_positions.append((excel_row, col_idx, row.get(img_col)))
        else:
            img_positions.append((excel_row, 1, None))

    for r, c, url in img_positions:
        if not url:
            continue
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img_bytes = BytesIO(resp.content)
            pil_img = Image.open(img_bytes).convert("RGB")

            # Resize proporsional ke lebar max_img_width
            w, h = pil_img.size
            if w > max_img_width:
                ratio = max_img_width / float(w)
                pil_img = pil_img.resize((int(w * ratio), int(h * ratio)))

            out = BytesIO()
            pil_img.save(out, format="PNG")
            out.seek(0)
            xl_img = XLImage(out)
            # Pindahkan ke sel (A=65)
            cell_ref = f"{chr(64 + c)}{r}"
            ws.add_image(xl_img, cell_ref)
            ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, pil_img.height * 0.75)
        except Exception:
            pass

    raw = io.BytesIO()
    wb.save(raw)
    raw.seek(0)
    return raw.getvalue()

def scrape_channel(channel_url: str, limit: Optional[int] = None):
    """Ambil iterator daftar video via scrapetube (tanpa API)."""
    return scrapetube.get_channel(channel_url=channel_url), limit

# ========= Streamlit App =========
st.set_page_config(page_title="YouTube Scraper (No API)", page_icon="▶️", layout="wide")
st.title("YouTube Scraper (tanpa API)")

with st.sidebar:
    st.header("Pengaturan")
    channel_url = st.text_input(
        "URL Channel atau @handle",
        placeholder="https://www.youtube.com/@NamaChannel atau https://www.youtube.com/channel/UC...",
    )
    start_date_inp = st.date_input("Tanggal awal (opsional)", value=None, format="YYYY-MM-DD")
    end_date_inp = st.date_input("Tanggal akhir (opsional)", value=None, format="YYYY-MM-DD")
    limit = st.number_input("Ambil maksimal", min_value=1, max_value=5000, value=50, step=10)
    st.caption("Catatan: Filter tanggal memerlukan yt-dlp untuk mendapatkan tanggal upload yang pasti.")
    enrich_toggle = st.toggle("Ambil deskripsi & like_count", value=True,
                              help="Menggunakan yt-dlp. Direkomendasikan agar tanggal upload pasti tersedia.")

col_btn1, col_btn2 = st.columns([1, 1])
with col_btn1:
    do_scrape = st.button("Mulai Scrape", type="primary", use_container_width=True)
with col_btn2:
    clear_data = st.button("Bersihkan Data", use_container_width=True)

if "df" not in st.session_state:
    st.session_state.df = None

if clear_data:
    st.session_state.df = None
    st.toast("Data direset.")

if do_scrape:
    if not channel_url.strip():
        st.error("Mohon isi URL channel terlebih dahulu.")
    elif (start_date_inp or end_date_inp) and not YTDLP_AVAILABLE:
        st.error("Filter tanggal memerlukan yt-dlp. Jalankan: `pip install yt-dlp` lalu jalankan ulang app.")
    else:
        try:
            with st.status("Menyiapkan…", expanded=False):
                videos_iter, lim = scrape_channel(channel_url.strip(), int(limit))

            rows = []
            total_est = int(limit)
            prog = st.progress(0, text="Mengambil daftar video…")
            counted = 0

            for v in videos_iter:
                vid = v.get("videoId")
                if not vid:
                    continue

                title = extract_text(safe_get(v, ["title"], {})) or "(Tanpa judul)"
                length_text = extract_text(safe_get(v, ["lengthText"], {}))
                thumb = build_thumb_url(vid, "hq")
                url = f"https://www.youtube.com/watch?v={vid}"

                meta = {"published_date": None, "description": None, "like_count": None}
                # Ambil tanggal/desc/like_count via yt_dlp jika diaktifkan atau diperlukan filter tanggal
                need_date = bool(start_date_inp or end_date_inp)
                if enrich_toggle or need_date:
                    fetched = ytdlp_fetch(url)
                    meta.update(fetched)

                row = {
                    "thumbnail_url": thumb,
                    "title": title,
                    "published_text": extract_text(safe_get(v, ["publishedTimeText"], {})),  # relatif
                    "published_date": meta["published_date"],  # YYYY-MM-DD
                    "duration_text": length_text,
                    "like_count": meta["like_count"],
                    "video_url": url,
                    "video_id": vid,
                    "description": meta["description"],
                }

                # Filter tanggal (inklusif)
                sd = start_date_inp if isinstance(start_date_inp, date) else None
                ed = end_date_inp if isinstance(end_date_inp, date) else None
                if in_date_range(row["published_date"], sd, ed):
                    rows.append(row)

                counted += 1
                prog.progress(min(counted / total_est, 1.0), text=f"Memproses video… {counted}/{total_est}")
                if counted >= total_est:
                    break

            if not rows:
                st.warning("Tidak ada video yang cocok. Periksa URL/handle, limit, atau rentang tanggal.")
            else:
                df = pd.DataFrame(rows)
                preferred_cols = [
                    "thumbnail_url", "title", "published_date", "published_text",
                    "duration_text", "like_count", "video_url", "video_id", "description"
                ]
                existing = [c for c in preferred_cols if c in df.columns]
                rest = [c for c in df.columns if c not in existing]
                df = df[existing + rest].copy()

                st.session_state.df = df
                st.success(f"Selesai. Total baris: {len(df)}")

        except Exception as e:
            st.error(f"Gagal mengambil data channel. Detail: {e}")

# ===== Preview + Download + Galeri (tetap tampil setelah klik) =====
if st.session_state.df is not None and not st.session_state.df.empty:
    st.subheader("Preview Data")

    st.data_editor(
        st.session_state.df,
        hide_index=True,
        height=520,
        use_container_width=True,
        column_config={
            "thumbnail_url": st.column_config.ImageColumn("Thumbnail"),
            "video_url": st.column_config.LinkColumn("Link Video"),
            "published_date": st.column_config.TextColumn("Tanggal (YYYY-MM-DD)"),
            "like_count": st.column_config.NumberColumn("Like"),
        },
        disabled=True,
    )

    # Download section
    st.subheader("Download")
    col_d1, col_d2 = st.columns(2)

    csv_buf = st.session_state.df.to_csv(index=False, encoding="utf-8-sig")
    with col_d1:
        st.download_button(
            "Download CSV",
            data=csv_buf,
            file_name="youtube_scrape.csv",
            mime="text/csv",
            use_container_width=True,
        )

    try:
        xlsx_bytes = create_excel_with_images(st.session_state.df, img_col="thumbnail_url", max_img_width=160)
        with col_d2:
            st.download_button(
                "Download Excel (dengan gambar)",
                data=xlsx_bytes,
                file_name="youtube_scrape.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    except Exception as e:
        st.error(f"Gagal membuat Excel dengan gambar: {e}")
        with col_d2:
            fallback = io.BytesIO()
            with pd.ExcelWriter(fallback, engine="openpyxl") as writer:
                st.session_state.df.to_excel(writer, index=False, sheet_name="videos")
            fallback.seek(0)
            st.download_button(
                "Download Excel (tanpa gambar)",
                data=fallback.getvalue(),
                file_name="youtube_scrape.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    # Galeri Grid (klik buka video)
    st.subheader("Galeri")
    thumbs_per_row = 5
    df_show = st.session_state.df[["thumbnail_url", "title", "video_url", "published_date"]].copy()
    rows = df_show.to_dict(orient="records")

    for i in range(0, len(rows), thumbs_per_row):
        cols = st.columns(thumbs_per_row)
        for j, item in enumerate(rows[i:i+thumbs_per_row]):
            with cols[j]:
                # HTML agar thumbnail bisa diklik
                html = f"""
                <div style="text-align:center">
                  <a href="{item['video_url']}" target="_blank" rel="noopener">
                    <img src="{item['thumbnail_url']}" style="width:100%; border-radius:12px;"/>
                  </a>
                  <div style="font-size:0.9rem; margin-top:6px;"><b>{item.get('published_date') or '-'}</b></div>
                  <div style="font-size:0.85rem; line-height:1.2; margin-top:4px;">{item['title']}</div>
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)

else:
    st.info("Masukkan URL/@handle, atur limit/tanggal (opsional), lalu klik **Mulai Scrape**.")

# FAQ ringkas
with st.expander("ℹ️ Catatan & Batasan"):
    st.markdown(
        """
- **Tanpa API** → data berasal dari struktur halaman YouTube via `scrapetube`. Struktur dapat berubah sewaktu-waktu.
- `published_date (YYYY-MM-DD)` diambil dengan **yt-dlp**. Jika tidak terpasang, filter tanggal tidak akan berfungsi.
- `like_count` sering `None` (YouTube menyembunyikan).
- Excel “dengan gambar” menempelkan thumbnail agar file lebih menarik.
- Progress bar menunjukkan jumlah item yang sedang diproses hingga mencapai limit.
        """
    )
