# app.py
# Hub Streamlit untuk memilih scraper: Instagram / YouTube / X (Twitter) / TikTok

import os
import runpy
import inspect
import importlib.util
import streamlit as st

# --- Konfigurasi halaman utama (aman jika modul anak juga memanggilnya) ---
try:
    st.set_page_config(page_title="Universal Scraper Hub", layout="wide")
except Exception:
    pass

st.title("🧰 Universal Scraper Hub")

# --- Sidebar pilihan platform ---
st.sidebar.header("Pilih Platform")
choice = st.sidebar.radio(
    "Platform",
    ["Instagram", "YouTube", "X (Twitter)", "TikTok"],  # <---- Tambah TikTok
    index=0,
    key="hub_platform_choice",
)

# Pemetaan pilihan -> (file python, key_prefix unik)
MODULE_MAP = {
    "Instagram": ("instagram.py", "ig_"),
    "YouTube": ("youtube.py", "yt_"),
    "X (Twitter)": ("x.py", "x_"),
    "TikTok": ("tiktok.py", "tt_"),  # <---- Tambah TikTok
}

filepath, key_prefix = MODULE_MAP[choice]
abs_path = os.path.abspath(filepath)

st.caption(f"Menjalankan modul: `{filepath}`")
st.write(f"**Lokasi:** `{abs_path}`")

def _load_module_from_path(module_name: str, path: str):
    """Muat modul python dari path tanpa mengganggu modul lain."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Tidak bisa membuat spec untuk modul dari: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
    except Exception as e:
        raise RuntimeError(f"Gagal import modul {module_name} dari {path}: {e}") from e
    return module

def _call_with_optional_kw(fn, **kwargs):
    """Panggil fungsi dengan hanya argumen yang didukung oleh signaturenya."""
    try:
        sig = inspect.signature(fn)
        accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return fn(**accepted) if accepted else fn()
    except TypeError:
        # Kompat modul lama: coba kirim 'st', lalu tanpa argumen
        try:
            return fn(st)
        except Exception:
            return fn()

def _run_module_ui(path: str, prefix: str):
    """
    Urutan eksekusi UI modul:
      1) render_app(key_prefix=prefix)
      2) render(key_prefix=prefix)
      3) main(key_prefix=prefix)
      4) Fallback: eksekusi file sebagai skrip
    """
    module_name = f"_scraper_{os.path.splitext(os.path.basename(path))[0]}"
    try:
        mod = _load_module_from_path(module_name, path)
    except Exception as e:
        st.error(str(e))
        return

    for candidate in ("render_app", "render", "main"):
        fn = getattr(mod, candidate, None)
        if callable(fn):
            try:
                _call_with_optional_kw(fn, key_prefix=prefix)
            except Exception as e:
                st.error(f"Error saat menjalankan {candidate}() di {path}: {e}")
            else:
                return  # sukses

    # Fallback: eksekusi file apa adanya
    try:
        runpy.run_path(path, init_globals={"st": st})
    except Exception as e:
        pass

# Validasi file modul
if not os.path.exists(abs_path):
    st.error(f"File `{filepath}` tidak ditemukan di direktori ini.")
else:
    _run_module_ui(abs_path, key_prefix)
