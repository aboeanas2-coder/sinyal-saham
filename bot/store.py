"""Penyimpanan sederhana berbasis file JSON (di-commit balik ke repo oleh GitHub Actions)."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
PORTFOLIO = DATA / "portfolio.json"
WIB = timezone(timedelta(hours=7))


def now():
    return datetime.now(WIB)


def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def portfolio():
    import config as C
    p = load(PORTFOLIO, {})
    p.setdefault("modal", C.MODAL)
    p.setdefault("positions", [])   # posisi terbuka
    p.setdefault("closed", [])      # riwayat transaksi selesai
    p.setdefault("signals", [])     # sinyal beli terakhir (untuk default lot saat /beli)
    p.setdefault("tg_offset", 0)
    p.setdefault("alerts", {})      # {KODE: tanggal} agar sinyal jual tidak dikirim berulang
    return p


def cash(p):
    invested = sum(x["entry"] * x["lots"] * 100 for x in p["positions"])
    realized = sum(x.get("pnl", 0) for x in p["closed"])
    return p["modal"] + realized - invested
