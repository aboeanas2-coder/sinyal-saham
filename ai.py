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


def _gemini_candidates(client):
    """Model dari config dulu, lalu model 'flash' yang benar-benar tersedia untuk kunci ini."""
    names = list(C.GEMINI_MODELS)
    try:
        found = []
        for m in client.models.list():
            name = (m.name or "").removeprefix("models/")
            actions = getattr(m, "supported_actions", None) or []
            if "flash" in name and "generateContent" in actions and not any(
                    w in name for w in ("image", "tts", "audio", "live", "embedding")):
                found.append(name)
        # utamakan versi stabil (tanpa 'preview'/'exp'), dari yang terbaru
        stable = sorted((n for n in found if "preview" not in n and "exp" not in n), reverse=True)
        others = [n for n in found if n not in stable]
        names += [n for n in stable + others if n not in names]
        print("Model Gemini tersedia:", ", ".join(stable + others) or "-")
    except Exception as e:
        print("Gagal membaca daftar model Gemini:", e)
    return names


def _gemini(prompt):
    import time

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    cfg = types.GenerateContentConfig(system_instruction=SYSTEM)
    last_err = None
    for model in _gemini_candidates(client)[:8]:
        for attempt in range(3):
            try:
                resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
                if resp.text:
                    print(f"Catatan AI dibuat oleh {model}")
                    return resp.text
                break
            except Exception as e:
                last_err, msg = e, str(e)
                print(f"Gemini {model} gagal (percobaan {attempt + 1}):", msg[:200])
                if any(k in msg for k in ("503", "UNAVAILABLE", "overloaded", "500", "INTERNAL")):
                    time.sleep(10 * (attempt + 1))  # server sibuk: tunggu lalu coba lagi
                    continue
                if any(k in msg for k in ("API key not valid", "API_KEY_INVALID", "PERMISSION_DENIED")):
                    raise  # kunci bermasalah: model lain juga pasti gagal
                break      # 404 / kuota habis di model ini: coba model berikutnya
    raise RuntimeError(f"semua model Gemini gagal: {str(last_err)[:200]}")


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
