"""Analisis naratif oleh Claude. Angka & keputusan tetap dari kode; Claude menjelaskan & memberi catatan risiko."""
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


def commentary(payload):
    if not os.getenv("ANTHROPIC_API_KEY"):
        return ""
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.beta.messages.create(
            model=C.CLAUDE_MODEL,
            max_tokens=4000,
            system=SYSTEM,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)}],
        )
        if resp.stop_reason == "refusal":
            return ""
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        # aman untuk parse_mode HTML Telegram: escape semua, lalu izinkan <b> saja
        return html.escape(text, quote=False).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    except Exception as e:  # laporan tetap terkirim walau AI gagal
        print("AI error:", e)
        return ""
