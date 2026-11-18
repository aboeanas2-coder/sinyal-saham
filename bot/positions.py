"""Evaluasi posisi terbuka -> sinyal jual / cut loss (dipakai laporan harian & pemantau intraday)."""
import pandas as pd

import store
from market import rp
from strategy import check_exit


def evaluate(p, frames):
    """frames: {KODE: DataFrame dengan indikator}. Mengubah p di tempat, mengembalikan daftar sinyal jual baru."""
    today = store.now().strftime("%Y-%m-%d")
    sells = []
    for pos in p["positions"]:
        df = frames.get(pos["code"])
        if df is None or df.empty:
            continue
        row = df.iloc[-1]
        price = float(row["Close"])
        held = max(len(df.loc[pd.Timestamp(pos["date"]):]) - 1, 0)
        action, reason, pos["stop"], pos["high"] = check_exit(pos, price, row, held)
        pos["last"], pos["days"] = price, held
        pos["pct"] = round((price / pos["entry"] - 1) * 100, 2)
        pos["status"] = action or "TAHAN"
        if action and p["alerts"].get(pos["code"]) != today:
            p["alerts"][pos["code"]] = today
            sells.append({"code": pos["code"], "action": action, "reason": reason, "price": price,
                          "lots": pos["lots"], "pct": pos["pct"]})
    return sells


def sell_text(s):
    icon = "🔴" if s["action"] == "CUT LOSS" else "🟡" if s["action"] in ("JUAL", "TRAILING STOP") else "🟢"
    return (f"{icon} <b>{s['action']} {s['code']}</b> {s['lots']} lot ≈ {rp(s['price'])} ({s['pct']:+.1f}%)\n"
            f"   {s['reason']}\n   Setelah jual: /jual {s['code']} HARGA")
