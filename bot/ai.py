"""Catatan AI: menjelaskan hasil hitungan kode. Angka & keputusan tetap dari kode, bukan dari AI.

Pilihan AI (cukup isi salah satu secret di GitHub):
- GEMINI_API_KEY    -> Google Gemini (ada kuota gratis)
- ANTHROPIC_API_KEY -> Claude (berbayar)
Kalau keduanya kosong, laporan tetap terkirim tanpa catatan AI.
"""
import html
import json
import os

import config as C

SYSTEM = (
    "Anda analis teknikal saham BEI yang ringkas dan jujur. Anda menerima data hasil penyaringan "
    "kuantitatif (skor, tren, RSI, momentum) beserta sinyal beli/jual yang SUDAH diputuskan oleh "
    "aturan. Tugas Anda: tulis laporan penutupan dalam Bahasa Indonesia santai, maksimal 180 kata, "
    "format teks biasa untuk Telegram (boleh <b>tebal</b>, tanpa markdown). Isi: 1) kondisi IHSG "
    "singkat, 2) alasan singkat tiap sinyal beli dan risikonya, 3) komentar posisi terbuka dan "
    "sinyal jual, 4) satu kalimat peringatan bila pasar sedang lemah. Jangan mengubah angka, jangan "
    "menambah saham baru, jangan menjanjikan keuntungan."
)


def _gemini(prompt):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    last_err = None
    for model in C.GEMINI_MODELS:  # coba berurutan; kalau satu model sudah tidak ada, pakai berikutnya
        try:
            resp = client.models.generate_content(
                model=model, contents=prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM))
            if resp.text:
                return resp.text
        except Exception as e:
            print(f"Gemini {model} gagal:", e)
            last_err = e
    raise RuntimeError(f"semua model Gemini gagal: {last_err}")


def _claude(prompt):
    import anthropic
    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model=C.CLAUDE_MODEL,
        max_tokens=4000,
        system=SYSTEM,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "refusal":
        return ""
    return "".join(b.text for b in resp.content if b.type == "text")


def commentary(payload):
    prompt = json.dumps(payload, ensure_ascii=False, default=str)
    try:
        if os.getenv("GEMINI_API_KEY"):
            text = _gemini(prompt)
        elif os.getenv("ANTHROPIC_API_KEY"):
            text = _claude(prompt)
        else:
            return ""
        text = text.strip().replace("**", "")  # buang sisa markdown tebal
        # aman untuk parse_mode HTML Telegram: escape semua, lalu izinkan <b> saja
        return html.escape(text, quote=False).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    except Exception as e:  # laporan tetap terkirim walau AI gagal
        print("AI error:", e)
        return ""
