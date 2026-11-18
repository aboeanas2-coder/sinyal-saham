"""Laporan penutupan harian (jalan 16:30 WIB, Senin-Jumat).

python bot/daily.py          -> jalan hanya kalau ada data hari bursa baru
python bot/daily.py --force  -> paksa jalan (untuk uji coba)
"""
import sys

import pandas as pd

import ai
import commands
import config as C
import positions
import store
import telegram
from market import add_indicators, download, round_tick, rp
from strategy import backtest, initial_stop, is_buy_setup, size_lots


def row_info(code, df):
    r = df.iloc[-1]
    prev = df["Close"].iloc[-2]
    return {"code": code, "price": float(r["Close"]), "chg": round((r["Close"] / prev - 1) * 100, 2),
            "score": None if pd.isna(r["SCORE"]) else int(r["SCORE"]),
            "ret3m": None if pd.isna(r["RET3M"]) else round(r["RET3M"] * 100, 1),
            "rsi": round(float(r["RSI"])), "trend": r["TREND"],
            "ma20": round(float(r["MA20"]), 1) if pd.notna(r["MA20"]) else None,
            "ma50": round(float(r["MA50"]), 1) if pd.notna(r["MA50"]) else None}


def chart_json(code, df, market_ok=None):
    d = df.iloc[-250:]
    marks = [m for m in backtest(df, market_ok) if m["date"] >= d.index[0].strftime("%Y-%m-%d")]
    rnd = lambda s: [None if pd.isna(v) else round(float(v), 1) for v in s]
    return {"code": code, "dates": [x.strftime("%Y-%m-%d") for x in d.index],
            "ohlc": [[float(o), float(c), float(l), float(h)] for o, c, l, h in
                     zip(d["Open"], d["Close"], d["Low"], d["High"])],
            "ma20": rnd(d["MA20"]), "ma50": rnd(d["MA50"]), "marks": marks}


def main(force=False):
    p = store.portfolio()
    commands.process(p)  # catat /beli /jual yang masuk sebelum laporan
    held = [x["code"] for x in p["positions"]]
    codes = sorted(set(C.UNIVERSE + C.WATCHLIST + held))
    raw = download(codes + [C.INDEX_TICKER], period="2y")
    ihsg = raw.pop(C.INDEX_TICKER, None)
    today = store.now().strftime("%Y-%m-%d")
    data_date = ihsg.index[-1].strftime("%Y-%m-%d") if ihsg is not None else today
    # Lapor sekali per hari bursa baru. Kalau Yahoo telat / bursa libur, data_date belum berubah -> lewati;
    # jadwal cadangan (17:30 & 06:30 WIB) akan mengirimnya begitu datanya muncul.
    if data_date == p.get("last_data_date") and not force:
        print(f"Belum ada data bursa baru (data terakhir {data_date}). Tidak ada laporan.")
        store.save(store.PORTFOLIO, p)
        return

    frames = {c: add_indicators(df) for c, df in raw.items() if len(df) > 60}
    rows = {c: row_info(c, df) for c, df in frames.items()}

    # 1) sinyal jual untuk posisi yang dipegang
    sells = positions.evaluate(p, frames)

    # 2) sinyal beli baru
    slots = C.MAX_POSISI - len(p["positions"])
    cash = store.cash(p)
    buys = []
    ranked = sorted((c for c in C.UNIVERSE if c in frames and rows[c]["score"] is not None),
                    key=lambda c: rows[c]["score"], reverse=True)
    # Filter pasar: backtest 2 tahun menunjukkan beli saat IHSG di bawah MA50 kebanyakan rugi.
    market_ok = (ihsg["Close"] > ihsg["Close"].rolling(50).mean()) if ihsg is not None else None
    pasar_sehat = market_ok is None or bool(market_ok.iloc[-1])
    for c in (ranked if pasar_sehat else []):
        if len(buys) >= min(slots, C.MAX_SINYAL_PER_HARI) or c in held:
            continue
        r = frames[c].iloc[-1]
        if not is_buy_setup(r):
            continue
        entry = float(r["Close"])
        stop = initial_stop(entry, r["ATR"])
        lots = size_lots(entry, stop, p["modal"], cash)
        if lots < 1:
            continue
        cash -= lots * 100 * entry
        buys.append({**rows[c], "lots": lots, "stop": stop, "cost": round(lots * 100 * entry),
                     "target": round_tick(entry * (1 + C.TARGET_PERSEN), up=True)})
    p["signals"] = [{"code": b["code"], "lots": b["lots"], "date": today} for b in buys]

    top10 = [rows[c] for c in ranked[:10]]
    watch = [rows[c] for c in C.WATCHLIST if c in rows]
    movers = sorted((rows[c] for c in C.UNIVERSE if c in rows), key=lambda x: x["chg"])
    ihsg_info = {"close": round(float(ihsg["Close"].iloc[-1])),
                 "chg": round((ihsg["Close"].iloc[-1] / ihsg["Close"].iloc[-2] - 1) * 100, 2)} if ihsg is not None else {}
    closed_today = [x for x in p["closed"] if x.get("exit_date") == today]

    # 3) analisis AI
    note = ai.commentary({"tanggal": data_date, "ihsg": ihsg_info, "ihsg_di_atas_ma50": pasar_sehat, "sinyal_beli": buys,
                          "sinyal_jual": sells, "posisi": p["positions"], "top10": top10[:5],
                          "naik_terbesar": movers[-3:], "turun_terbesar": movers[:3]})

    # 4) kirim laporan ke Telegram
    lines = [f"📊 <b>Laporan BEI {data_date}</b>",
             f"IHSG {rp(ihsg_info.get('close', 0))} ({ihsg_info.get('chg', 0):+.2f}%)", ""]
    if closed_today:
        lines.append("<b>Transaksi hari ini</b>")
        lines += [f"• Jual {x['code']} @ {rp(x['exit'])} → Rp {rp(x['pnl'])} ({x['pct']:+.1f}%)" for x in closed_today]
        lines.append("")
    if sells:
        lines.append("<b>⚠️ Sinyal jual</b>")
        lines += [positions.sell_text(s) for s in sells]
        lines.append("")
    if p["positions"]:
        lines.append("<b>Posisi</b>")
        lines += [f"• {x['code']} {x['lots']} lot {x['pct']:+.1f}% · stop {rp(x['stop'])} · {x['status']}" for x in p["positions"]]
        lines.append("")
    if buys:
        lines.append(f"🔔 <b>Sinyal beli untuk besok pagi</b> (modal Rp {rp(p['modal'])})")
        for b in buys:
            lines.append(f"• <b>{b['code']}</b> {b['lots']} lot ≈ {rp(b['price'])} (Rp {rp(b['cost'])})\n"
                         f"   skor {b['score']} · RSI {b['rsi']} · stop {rp(b['stop'])} · target {rp(b['target'])}")
        lines.append("Setelah beli di Stockbit, lapor: /beli KODE HARGA LOT")
    elif not pasar_sehat:
        lines.append("Tidak ada sinyal beli: IHSG masih di bawah rata-rata 50 hari, sinyal beli ditahan dulu.")
    else:
        lines.append("Tidak ada sinyal beli hari ini.")
    if note:
        lines += ["", "🤖 <b>Catatan AI</b>", note]
    if C.DASHBOARD_URL:
        lines += ["", C.DASHBOARD_URL]
    telegram.send("\n".join(lines))

    # 5) simpan untuk dashboard
    chart_codes = set(C.WATCHLIST + [r["code"] for r in top10] + [b["code"] for b in buys]
                      + [x["code"] for x in p["positions"]])
    for c in chart_codes:
        if c in frames:
            store.save(store.DATA / "chart" / f"{c}.json", chart_json(c, frames[c], market_ok))
    store.save(store.DATA / "summary.json", {
        "updated": store.now().strftime("%d-%m-%Y %H:%M"), "data_date": data_date, "ihsg": ihsg_info,
        "modal": p["modal"], "cash": round(store.cash(p)), "buys": buys, "sells": sells,
        "top10": top10, "watch": watch, "ai": note, "charts": sorted(chart_codes & set(frames)),
        "positions": p["positions"], "closed": p["closed"][-20:]})
    p["last_data_date"] = data_date
    store.save(store.PORTFOLIO, p)
    print(f"Selesai: {len(buys)} sinyal beli, {len(sells)} sinyal jual, {len(chart_codes)} chart.")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
