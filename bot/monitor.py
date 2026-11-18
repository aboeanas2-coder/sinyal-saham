"""Jalan tiap 15 menit: baca perintah Telegram, dan saat jam bursa cek cut loss posisi Anda."""
import commands
import positions
import store
import telegram
from market import add_indicators, download


def market_open():
    n = store.now()
    return n.weekday() < 5 and (9, 0) <= (n.hour, n.minute) <= (16, 0)


def main():
    p = store.portfolio()
    commands.process(p)
    if market_open() and p["positions"]:
        raw = download([x["code"] for x in p["positions"]], period="6mo")
        frames = {c: add_indicators(df) for c, df in raw.items()}
        sells = positions.evaluate(p, frames)
        if sells:
            telegram.send("⏰ <b>Pantauan intraday</b>\n" + "\n".join(positions.sell_text(s) for s in sells))
    store.save(store.PORTFOLIO, p)


if __name__ == "__main__":
    main()
