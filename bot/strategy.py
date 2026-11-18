"""Aturan beli, ukuran lot, aturan jual/cut loss, dan backtest untuk penanda di chart."""
import math

import pandas as pd

import config as C
from market import rp
from market import round_tick


def is_buy_setup(row):
    return (row["SCORE"] >= C.SKOR_MIN_BELI and row["TREND"] == "naik"
            and C.RSI_BELI[0] <= row["RSI"] <= C.RSI_BELI[1]
            and row["VALUE20"] >= C.NILAI_TRANSAKSI_MIN)


def initial_stop(entry, atr):
    stop = max(entry - C.STOP_ATR * atr, entry * (1 - C.STOP_MAX_PERSEN))
    return round_tick(stop)


def size_lots(entry, stop, modal, cash):
    """Lot yang disarankan: dibatasi jatah per posisi, risiko 2% modal, dan kas tersisa."""
    per_share_risk = max(entry - stop, 1)
    by_alloc = (modal / C.MAX_POSISI) / entry
    by_risk = (modal * C.RISIKO_PER_TRADE) / per_share_risk
    by_cash = cash / entry
    return int(math.floor(min(by_alloc, by_risk, by_cash) / C.LOT))


def check_exit(pos, price, row, days_held):
    """Kembalikan (aksi|None, alasan, stop_baru, high_baru)."""
    entry = pos["entry"]
    high = max(pos.get("high", entry), price)
    stop = pos["stop"]
    if pd.notna(row["ATR"]) and high > entry:
        stop = max(stop, round_tick(high - C.TRAIL_ATR * row["ATR"]))
    target = pos.get("target") or round_tick(entry * (1 + C.TARGET_PERSEN), up=True)
    gain = price / entry - 1

    if price <= stop:
        kind = "CUT LOSS" if price < entry else "TRAILING STOP"
        return kind, f"harga {rp(price)} menyentuh stop {rp(stop)}", stop, high
    if price >= target:
        return "AMBIL UNTUNG", f"target {rp(target)} tercapai ({gain:+.1%})", stop, high
    if pd.notna(row["MA50"]) and row["Close"] < row["MA50"] and price < entry:
        return "CUT LOSS", f"tren patah: tutup di bawah MA50 ({rp(row['MA50'])})", stop, high
    if days_held >= C.HORIZON_HARI and gain < 0.03:
        return "JUAL", f"{days_held} hari bursa, hasil {gain:+.1%} — prediksi tidak terbukti", stop, high
    return None, "", stop, high


def backtest(df, market_ok=None):
    """Simulasi aturan yang sama di data historis -> penanda beli/jual untuk chart.
    market_ok: Series bool per tanggal (IHSG > MA50); bila diisi, beli hanya saat pasar sehat."""
    marks, pos = [], None
    ok = market_ok.reindex(df.index).fillna(False).astype(bool) if market_ok is not None else None
    for i in range(len(df) - 1):
        r = df.iloc[i]
        if pos is None:
            if pd.notna(r["SCORE"]) and is_buy_setup(r) and (ok is None or ok.iloc[i]):
                nxt = df.iloc[i + 1]
                entry = float(nxt["Open"])
                pos = {"entry": entry, "stop": initial_stop(entry, r["ATR"]), "high": entry, "i": i + 1}
                marks.append({"date": df.index[i + 1].strftime("%Y-%m-%d"), "type": "buy", "price": entry})
        else:
            if i < pos["i"]:
                continue
            price = float(r["Close"])
            action, _, pos["stop"], pos["high"] = check_exit(pos, price, r, i - pos["i"])
            if action:
                pct = price / pos["entry"] - 1
                marks.append({"date": df.index[i].strftime("%Y-%m-%d"), "type": "sell",
                              "price": price, "pct": round(pct * 100, 1), "reason": action})
                pos = None
    return marks
