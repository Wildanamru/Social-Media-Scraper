# Social Media Scraper  
### Dashboard Streamlit untuk Scraping Instagram, YouTube, X (Twitter), dan TikTok

## 📌 Deskripsi
**Social Media Scraper** adalah aplikasi dashboard berbasis **Streamlit** yang memudahkan kamu melakukan scraping data dari berbagai platform populer:

- **Instagram**
- **YouTube**
- **X (Twitter)**
- **TikTok**

Dengan aplikasi ini, kamu bisa:
- Mengambil metadata postingan (tanggal, link, caption, jumlah like, views, komentar, shares).
- Melihat hasil scraping dalam bentuk **tabel interaktif** langsung di dashboard.
- Menyaring data berdasarkan **rentang tanggal**.
- Menyimpan hasil scraping ke dalam format **CSV** atau **Excel (dengan thumbnail gambar)**.
- Menggunakan **cookies (JSON)** untuk TikTok dan Instagram agar scraping lebih stabil dan thumbnail tidak blank. **Disarankan menggunakan extension cookie-editor untuk mengambil cookienya**

Aplikasi ini dirancang **modular**, sehingga setiap platform punya file Python terpisah (`instagram.py`, `youtube.py`, `x.py`, `tiktok.py`) dan dijalankan lewat hub utama `app.py`.

---

## ⚙️ Instalasi & Menjalankan Aplikasi

1. **Clone repository**
   ```bash
   git clone https://github.com/Wildanamru/Social-Media-Scraper.git
   cd Social-Media-Scraper

2. **Buat virtual environment**
    ```powershell
    python -m venv .venv

2. **Jalankan virtual environment**
    ```powershell
    .venv\Scripts\activate

3. **Install Library**
    ```powershell
    pip install -r reqruitment.txt

4. **Jalankan**
    ```powershell
    streamlit run app.py

