"""Pengaturan utama. Ubah angka di sini sesuai selera risiko Anda."""
import os

# ---- Modal & ukuran posisi ----
MODAL = int(os.getenv("MODAL", "3000000"))  # Rp, bisa juga diubah lewat Telegram: /modal 5000000
MAX_POSISI = 3            # maksimal saham dipegang bersamaan
RISIKO_PER_TRADE = 0.02   # rugi maksimal per transaksi = 2% modal
LOT = 100                 # 1 lot BEI = 100 lembar

# ---- Aturan sinyal beli ----
SKOR_MIN_BELI = 75        # skor 0-100
RSI_BELI = (50, 70)       # RSI harus di rentang ini (momentum sehat, belum terlalu jenuh beli)
NILAI_TRANSAKSI_MIN = 5e9 # rata-rata nilai transaksi harian 20 hari >= Rp 5 miliar (likuid)
MAX_SINYAL_PER_HARI = 3

# ---- Aturan jual / cut loss ----
STOP_ATR = 2.0            # stop awal = harga beli - 2 x ATR ...
STOP_MAX_PERSEN = 0.07    # ... tapi tidak lebih jauh dari -7%
TRAIL_ATR = 2.5           # trailing stop = harga tertinggi sejak beli - 2.5 x ATR
TARGET_PERSEN = 0.15      # ambil untung di +15%
HORIZON_HARI = 20         # ~4 pekan bursa; lewat ini & untung < 3% -> jual (prediksi tidak terbukti)

# ---- Daftar saham yang dipindai (likuid; tambah sesuka hati) ----
UNIVERSE = """
AADI AALI ACES ADMR ADRO AKRA AMMN AMRT ANTM ARTO ASII AUTO AVIA BBCA BBNI BBRI BBTN BDMN BFIN
BMRI BNGA BRIS BRPT BSDE BTPS BUKA CPIN CTRA DSNG EMTK ENRG ERAA ESSA EXCL GGRM GOTO HEAL HMSP
HRUM ICBP INCO INDF INDY INKP INTP ISAT ITMG JPFA JSMR KLBF MAPA MAPI MBMA MDKA MEDC MIKA MNCN
MTEL MYOR NCKL PGAS PGEO PNLF PTBA PTPP PWON RAJA SCMA SIDO SMGR SMRA SRTG SSMS TAPG TBIG TINS
TKIM TLKM TOWR TPIA UNTR UNVR WIFI
""".split()

# Pantauan khusus (selalu ditampilkan di dashboard & laporan)
WATCHLIST = "JSMR GOTO BUKA BELI EMTK DCII MTDL MLPT DMMX WIRG ARTO BBHI WIFI".split()

INDEX_TICKER = "^JKSE"

# ---- AI ----
CLAUDE_MODEL = "claude-opus-5-5"

# ---- Rahasia (diisi di GitHub > Settings > Secrets) ----
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "")
