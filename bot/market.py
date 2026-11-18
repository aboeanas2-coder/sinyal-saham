"""Ambil data harga (Yahoo Finance) dan hitung indikator + skor."""
import math

import numpy as np
import pandas as pd
import yfinance as yf


def download(codes, period="2y", interval="1d"):
    """Kembalikan dict {KODE: DataFrame(Open, High, Low, Close, Volume)}."""
    tickers = [c if c.startswith("^") else f"{c}.JK" for c in codes]
    raw = yf.download(tickers, period=period, interval=interval, group_by="ticker",
                      auto_adjust=False, progress=False, threads=True)
    out = {}
    for code, t in zip(codes, tickers):
        try:
            df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
        except KeyError:
            continue
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
        df = df[df["Volume"] > 0] if not code.startswith("^") else df
        if len(df) > 0:
            df.index = pd.to_datetime(df.index).tz_localize(None)
            out[code] = df
    return out


def rsi(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100)


def add_indicators(df):
    df = df.copy()
    c = df["Close"]
    df["MA20"] = c.rolling(20).mean()
    df["MA50"] = c.rolling(50).mean()
    df["RSI"] = rsi(c)
    tr = pd.concat([df["High"] - df["Low"],
                    (df["High"] - c.shift()).abs(),
                    (df["Low"] - c.shift()).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    df["RET1M"] = c / c.shift(21) - 1
    df["RET3M"] = c / c.shift(63) - 1
    df["VOLR"] = df["Volume"].rolling(5).mean() / df["Volume"].rolling(20).mean()
    df["VALUE20"] = (c * df["Volume"]).rolling(20).mean()
    df["HI52"] = c.rolling(250, min_periods=60).max()
    df["MA50_SLOPE"] = df["MA50"] / df["MA50"].shift(10) - 1

    # ---- Skor 0-100 (semakin tinggi = semakin berpotensi naik 3-4 pekan) ----
    trend = (10 * (c > df["MA20"]) + 10 * (df["MA20"] > df["MA50"]) + 10 * (df["MA50_SLOPE"] > 0))
    mom = (np.interp(df["RET3M"].fillna(0), [-0.2, 0.3], [0, 15])
           + np.interp(df["RET1M"].fillna(0), [-0.1, 0.15], [0, 10]))
    r = df["RSI"]
    rsi_pts = np.select([(r >= 50) & (r <= 65), (r > 65) & (r <= 70), (r >= 45) & (r < 50), r > 70],
                        [20, 12, 10, 4], 2)
    vol_pts = np.interp(df["VOLR"].fillna(1), [0.8, 2.0], [0, 15])
    near_hi = np.interp((c / df["HI52"]).fillna(0), [0.75, 0.95], [0, 10])
    df["SCORE"] = (trend + mom + rsi_pts + vol_pts + near_hi).round()
    df.loc[df["MA50"].isna(), "SCORE"] = np.nan

    up = (c > df["MA20"]) & (df["MA20"] > df["MA50"]) & (df["MA50_SLOPE"] > 0)
    down = (c < df["MA20"]) & (df["MA20"] < df["MA50"])
    df["TREND"] = np.select([up, down], ["naik", "turun"], "datar")
    return df


def tick(price):
    """Fraksi harga BEI."""
    if price < 200:
        return 1
    if price < 500:
        return 2
    if price < 2000:
        return 5
    if price < 5000:
        return 10
    return 25


def round_tick(price, up=False):
    t = tick(price)
    return int((math.ceil if up else math.floor)(price / t) * t)


def rp(x):
    """Format angka gaya Indonesia: 1234567 -> 1.234.567"""
    return f"{x:,.0f}".replace(",", ".")

