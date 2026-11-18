"""Perintah Telegram: /beli, /jual, /posisi, /modal, /bantuan."""
import config as C
from market import rp
import store
import telegram
from market import add_indicators, download, round_tick
from strategy import initial_stop

FEE_BELI, FEE_JUAL = 0.0015, 0.0025  # perkiraan fee Stockbit (beli 0,15%, jual 0,25% termasuk pajak)

HELP = ("<b>Perintah</b>\n"
        "/beli KODE HARGA [LOT] — catat pembelian, mis. /beli BBRI 4100 2\n"
        "/jual KODE HARGA — catat penjualan\n"
        "/posisi — lihat posisi & stop loss\n"
        "/modal JUMLAH — ubah modal, mis. /modal 5000000")


def _num(s):
    return float(s.replace(".", "").replace(",", "."))


def handle(p, text):
    parts = text.split()
    cmd = parts[0].lower().split("@")[0]
    try:
        if cmd == "/beli" and len(parts) >= 3:
            code, price = parts[1].upper(), _num(parts[2])
            sig = next((s for s in p["signals"] if s["code"] == code), None)
            lots = int(parts[3]) if len(parts) > 3 else (sig["lots"] if sig else 1)
            df = download([code], period="6mo").get(code)
            atr = float(add_indicators(df).iloc[-1]["ATR"]) if df is not None else price * 0.03
            existing = next((x for x in p["positions"] if x["code"] == code), None)
            if existing:  # tambah lot -> harga rata-rata
                total = existing["lots"] + lots
                existing["entry"] = round((existing["entry"] * existing["lots"] + price * lots) / total, 1)
                existing["lots"] = total
                pos = existing
            else:
                pos = {"code": code, "entry": price, "lots": lots, "date": store.now().strftime("%Y-%m-%d"),
                       "stop": initial_stop(price, atr), "high": price,
                       "target": round_tick(price * (1 + C.TARGET_PERSEN), up=True)}
                p["positions"].append(pos)
            return (f"✅ Tercatat beli <b>{code}</b> {lots} lot @ {rp(price)}\n"
                    f"Stop loss {rp(pos['stop'])} · target {rp(pos['target'])}. Saya pantau tiap 15 menit.")

        if cmd == "/jual" and len(parts) >= 3:
            code, price = parts[1].upper(), _num(parts[2])
            pos = next((x for x in p["positions"] if x["code"] == code), None)
            if not pos:
                return f"Tidak ada posisi {code}."
            shares = pos["lots"] * 100
            pnl = price * shares * (1 - FEE_JUAL) - pos["entry"] * shares * (1 + FEE_BELI)
            p["positions"].remove(pos)
            p["closed"].append({**pos, "exit": price, "exit_date": store.now().strftime("%Y-%m-%d"),
                                "pnl": round(pnl), "pct": round((price / pos["entry"] - 1) * 100, 2)})
            p["alerts"].pop(code, None)
            return f"✅ Tercatat jual <b>{code}</b> @ {rp(price)} · hasil <b>Rp {rp(pnl)}</b> ({price / pos['entry'] - 1:+.1%})"

        if cmd == "/posisi":
            if not p["positions"]:
                return "Belum ada posisi."
            return "\n".join(f"<b>{x['code']}</b> {x['lots']} lot @ {rp(x['entry'])} · stop {rp(x['stop'])} · "
                             f"target {rp(x['target'])}" for x in p["positions"])

        if cmd == "/modal" and len(parts) >= 2:
            p["modal"] = int(_num(parts[1]))
            return f"Modal diubah ke Rp {rp(p['modal'])}"
    except Exception as e:
        return f"Format salah ({e}).\n\n{HELP}"
    return HELP


def process(p):
    msgs, p["tg_offset"] = telegram.updates(p["tg_offset"])
    for m in msgs:
        if m.startswith("/"):
            telegram.send(handle(p, m))
    return len(msgs)
