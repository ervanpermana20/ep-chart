# Trading Chart App (XAUUSD, EURUSD, dll)

Chart candlestick + volume + EMA + RSI, mode replay (belajar baca chart pakai
data lama), drawing tools (trend line, kotak, TP/SL), dan panel AI chat
(Gemini) buat tanya-tanya soal pola chart.

## Arsitektur singkat

```
Browser (index.html + lightweight-charts)
        |  fetch /api/candles, /api/chat
        v
Flask server (app.py)  --> TwelveData API (data candle)
                        --> Gemini API (AI chat)
```

TwelveData bisa saja diakses langsung dari browser, tapi kita tetap lewat
server Flask supaya API key nggak keekspos di kode frontend yang bisa
dilihat siapa saja lewat "View Source". Server ini juga sekaligus yang
nyajiin file index.html, jadi kamu cuma perlu jalanin satu perintah.

## 1. Siapkan akun & API key

### TwelveData (data harga)
1. Daftar gratis di https://twelvedata.com (cukup email, nggak perlu kartu).
2. Setelah login, buka Dashboard — API key langsung kelihatan di situ.
3. Simpan key itu — ini yang dipakai sebagai `TWELVEDATA_API_KEY`.

Batasan free tier: sekitar 800 request/hari dan 8 request/menit (bisa
berubah, cek dashboard TwelveData buat angka pastinya). Instrument yang
didukung di app ini: `XAU_USD` (gold), `EUR_USD`, `GBP_USD`, `USD_JPY` —
di balik layar otomatis dikonversi ke format TwelveData (`XAU/USD`, dst),
kamu nggak perlu ubah apa-apa di frontend.

### Gemini (AI chat)
1. Buka https://aistudio.google.com/apikey, generate API key gratis.
2. Simpan sebagai `GEMINI_API_KEY`.

Model yang dipakai di `app.py` saat ini: `gemini-2.5-flash`. Kalau suatu
saat muncul error 404 dari Gemini, kemungkinan model ini sudah pensiun —
cek nama model terbaru di https://ai.google.dev/gemini-api/docs/models dan
ganti nilai `GEMINI_MODEL` di `app.py`.

## 2. Install & jalankan di Termux

```bash
cd trading-chart-app
pip install -r requirements.txt --break-system-packages

export TWELVEDATA_API_KEY="key_twelvedata_kamu"
export GEMINI_API_KEY="key_gemini_kamu"

python app.py
```

Kalau muncul `Running on http://0.0.0.0:5000`, buka Chrome/Brave di HP yang
sama, akses:

```
http://localhost:5000
```

Biar nggak perlu export ulang tiap buka Termux, taruh 3 baris `export` di
atas ke file `~/.bashrc` (atau `~/.zshrc` kalau pakai zsh).

## 3. Cara pakai fitur

- **Instrument & timeframe**: dropdown di kiri atas (M1/M5/M15/M30/H1/H4).
- **Cursor**: mode default, buat geser/zoom chart.
- **Trend Line / Kotak**: klik tombolnya, lalu klik 2 titik di chart.
- **TP / SL**: klik tombolnya, lalu klik satu titik harga di chart —
  langsung muncul garis horizontal di harga itu.
- **Hapus Gambar**: buang semua trend line/kotak/TP/SL yang sudah digambar.
- **Mode Replay**: geser slider di bawah chart, atau pakai tombol
  Step/Play untuk mainin ulang candle satu-satu dari data historis.
  Balik ke "Mode: Live" buat lihat data lengkap lagi.
- **AI Chat**: tombol "AI Chat" di kanan atas buka panel. Pertanyaan yang
  kamu ketik dikirim bareng data candle yang lagi kelihatan di chart.

## 4. Batasan yang perlu kamu tahu (jujur, bukan basa-basi)

- Ini **bukan** rekonstruksi penuh TradingView. Drawing tools masih versi
  dasar: sekali digambar nggak bisa di-drag/resize lagi. Kalau salah gambar,
  hapus semua lewat tombol "Hapus Gambar" dan gambar ulang.
- Analisa dari AI chat **bukan sinyal trading**. Itu deskripsi pola dari
  LLM berdasarkan angka OHLC yang dikirim, bisa salah, dan tidak tahu berita
  fundamental real-time kecuali kamu kasih tahu di pertanyaan.
- Free tier TwelveData ada limit harian & per-menit. Kalau kamu ganti
  timeframe/instrument bolak-balik terlalu cepat, bisa kena rate limit
  sementara — errornya akan muncul jelas di status bar app (bukan bug diam-diam).
- Forex & gold spot nggak punya data volume konsolidasi resmi, jadi bar
  volume di chart bisa kelihatan flat/kosong. Ini wajar, bukan bug —
  beda dengan saham/crypto yang volume-nya memang tercatat.
- Belum ada penyimpanan gambar/state — refresh halaman = drawing hilang.
  Ini bisa ditambah belakangan (simpan ke localStorage atau file) kalau
  memang kepakai.

## 5. Struktur file

```
trading-chart-app/
├── app.py              # backend Flask
├── requirements.txt
├── static/
│   └── index.html      # semua frontend (chart, drawing, replay, AI chat)
└── README.md
```
