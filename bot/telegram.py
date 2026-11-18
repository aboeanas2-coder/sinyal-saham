"""Kirim pesan & baca perintah Telegram (Telegram jalan di HP dan MacBook sekaligus)."""
import requests

import config as C

API = "https://api.telegram.org/bot{}/{}"


def send(text):
    if not C.TELEGRAM_TOKEN or not C.TELEGRAM_CHAT_ID:
        print("[telegram belum diatur]\n" + text)
        return
    for chunk in [text[i:i + 3900] for i in range(0, len(text), 3900)]:
        r = requests.post(API.format(C.TELEGRAM_TOKEN, "sendMessage"), timeout=30, json={
            "chat_id": C.TELEGRAM_CHAT_ID, "text": chunk,
            "parse_mode": "HTML", "disable_web_page_preview": True})
        if not r.ok:
            print("Telegram error:", r.text)


def updates(offset):
    """Pesan baru sejak offset, hanya dari chat milik Anda sendiri."""
    if not C.TELEGRAM_TOKEN:
        return [], offset
    r = requests.get(API.format(C.TELEGRAM_TOKEN, "getUpdates"),
                     params={"offset": offset, "timeout": 0}, timeout=30)
    r.raise_for_status()
    msgs = []
    for u in r.json().get("result", []):
        offset = max(offset, u["update_id"] + 1)
        m = u.get("message") or {}
        if str(m.get("chat", {}).get("id")) == str(C.TELEGRAM_CHAT_ID) and m.get("text"):
            msgs.append(m["text"].strip())
    return msgs, offset
