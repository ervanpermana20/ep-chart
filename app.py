"""
Backend untuk Trading Chart App.

Fungsi server ini:
1. Proxy ke OANDA v20 REST API buat ambil data candle (OANDA nggak bisa
   diakses langsung dari browser karena CORS, jadi harus lewat server).
2. Proxy ke Gemini API buat fitur chat AI (biar API key nggak keekspos
   ke browser).
3. Serve file frontend (index.html) di folder static/.

Cara pakai:
    export OANDA_API_KEY="token_practice_account_kamu"
    export GEMINI_API_KEY="api_key_gemini_kamu"
    python app.py

Lalu buka http://localhost:5000 di Chrome/Brave.
"""

import os
import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="")

TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

TWELVEDATA_BASE = "https://api.twelvedata.com"

# Mapping timeframe frontend -> format interval TwelveData
GRANULARITY_MAP = {
    "M1": "1min", "M5": "5min", "M15": "15min",
    "M30": "30min", "H1": "1h", "H4": "4h",
}

# Mapping instrument frontend (format lama OANDA pakai underscore) -> format TwelveData pakai slash
INSTRUMENT_MAP = {
    "XAU_USD": "XAU/USD",
    "EUR_USD": "EUR/USD",
    "GBP_USD": "GBP/USD",
    "USD_JPY": "USD/JPY",
    "BTC_USD": "BTC/USD",
}

# Model Gemini yang dipakai buat chat. Per Juni 2026 seri Gemini 2.x sudah
# dimatikan total oleh Google. Kalau suatu saat error 404 lagi, cek model
# terbaru di https://ai.google.dev/gemini-api/docs/models
GEMINI_MODEL = "gemini-3.5-flash"


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/candles")
def get_candles():
    instrument = request.args.get("instrument", "XAU_USD")
    granularity = request.args.get("granularity", "M15")
    count = request.args.get("count", "500")

    if granularity not in GRANULARITY_MAP:
        return jsonify({"error": f"Timeframe {granularity} tidak didukung"}), 400

    if instrument not in INSTRUMENT_MAP:
        return jsonify({"error": f"Instrument {instrument} tidak didukung"}), 400

    if not TWELVEDATA_API_KEY:
        return jsonify({
            "error": "TWELVEDATA_API_KEY belum diset. Jalankan: export TWELVEDATA_API_KEY=key_kamu"
        }), 500

    symbol = INSTRUMENT_MAP[instrument]
    interval = GRANULARITY_MAP[granularity]

    url = f"{TWELVEDATA_BASE}/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": count,
        "order": "asc",       # biar urutannya lama -> baru, sesuai yang dipakai frontend
        "timezone": "UTC",    # biar konsisten, nggak ikut timezone bursa yang beda-beda
        "apikey": TWELVEDATA_API_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Gagal konek ke TwelveData: {str(e)}"}), 502

    data = resp.json()

    if data.get("status") == "error":
        return jsonify({
            "error": f"TwelveData menolak request: {data.get('message', 'unknown error')}"
        }), 502

    candles = []
    for v in data.get("values", []):
        try:
            candles.append({
                "time": v["datetime"].replace(" ", "T") + "Z",
                "open": float(v["open"]),
                "high": float(v["high"]),
                "low": float(v["low"]),
                "close": float(v["close"]),
                # forex/gold spot nggak punya volume konsolidasi resmi, TwelveData
                # kadang isi 0 atau kosong buat pair non-crypto/non-stock. Ini normal.
                # BTC/USD (crypto) beda: TwelveData kasih volume asli dari exchange.
                "volume": float(v.get("volume") or 0),
            })
        except (KeyError, ValueError, TypeError):
            continue  # skip baris data yang formatnya nggak sesuai dugaan

    # Chart butuh data terurut naik & tanpa timestamp dobel, atau library
    # frontend bisa gagal render / kelihatan aneh (misal jadi garis datar).
    # Kita jamin ini di backend, jangan asumsikan provider selalu konsisten.
    candles.sort(key=lambda c: c["time"])
    deduped = []
    seen_time = None
    for c in candles:
        if c["time"] == seen_time:
            deduped[-1] = c  # kalau ada timestamp dobel, pakai yang paling akhir muncul
        else:
            deduped.append(c)
            seen_time = c["time"]
    candles = deduped

    return jsonify({"candles": candles, "instrument": instrument, "granularity": granularity})


@app.route("/api/chat", methods=["POST"])
def chat():
    if not GEMINI_API_KEY:
        return jsonify({
            "error": "GEMINI_API_KEY belum diset. Jalankan: export GEMINI_API_KEY=key_kamu"
        }), 500

    body = request.get_json(force=True)
    question = (body.get("question") or "").strip()
    instrument = body.get("instrument", "")
    granularity = body.get("granularity", "")
    candles = body.get("candles", [])[-100:]  # batasi biar prompt nggak kepanjangan

    if not question:
        return jsonify({"error": "Pertanyaan kosong"}), 400

    candle_lines = "\n".join(
        f"{c['time']} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']}"
        for c in candles
    )

    prompt = f"""Kamu adalah asisten belajar membaca chart trading untuk instrumen {instrument},
timeframe {granularity}. Berikut {len(candles)} candle terakhir (urut dari paling lama ke paling baru):

{candle_lines}

Pertanyaan user: {question}

Instruksi jawaban:
- Bahasa Indonesia, langsung ke inti, tidak bertele-tele.
- Jelaskan pola price action yang kelihatan dari data di atas (struktur harga, support/resistance kasar, momentum).
- Sebutkan kecenderungan bullish/bearish HANYA berdasarkan data candle ini, bukan berdasarkan berita/fundamental
  yang tidak kamu punya datanya.
- Kalau user tanya soal fundamental dan kamu tidak yakin datanya update, katakan terus terang tidak yakin,
  jangan mengarang.
- WAJIB tutup jawaban dengan satu kalimat pengingat bahwa ini bantuan edukasi membaca chart,
  bukan rekomendasi/sinyal trading."""

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Gagal hubungi Gemini API: {str(e)}"}), 502

    data = resp.json()
    try:
        answer = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        answer = "Maaf, tidak ada respon yang bisa diambil dari AI. Coba tanya ulang."

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
