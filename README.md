# Sinyal Saham BEI

Bot gratis yang jalan sendiri di GitHub Actions:

| Kapan | Apa |
|---|---|
| **16:30 WIB** tiap hari bursa | Laporan penutupan + skor semua saham di daftar + **sinyal beli** (kode & jumlah lot) untuk besok pagi, plus catatan AI (Claude). Dikirim ke Telegram (HP & MacBook). |
| **Tiap 15 menit** saat jam bursa | Cek posisi Anda. Kalau kena stop loss / tren patah / target tercapai → **sinyal jual** ke Telegram. |
| Kapan saja | Lapor transaksi lewat Telegram: `/beli BBRI 4100 2`, `/jual BBRI 4350`, `/posisi`, `/modal 5000000` |

Dashboard (seperti contoh screenshot) ada di `docs/index.html`, ditayangkan lewat GitHub Pages.

## Cara kerja prediksi (3-4 pekan)

Skor 0-100 per saham dari: tren (harga > MA20 > MA50, MA50 menanjak), momentum 1 & 3 bulan, RSI, lonjakan volume, dan jarak ke harga tertinggi 52 minggu.
**Sinyal beli** muncul bila skor ≥ 75, tren naik, RSI 50-70, saham likuid (≥ Rp 5 M/hari), **dan IHSG di atas rata-rata 50 harinya**.

> Hasil uji 2 tahun (Nov 2024–Nov 2026, IHSG turun 7.134 → 5.305, 79 saham): tanpa filter IHSG 528 transaksi, menang 28%, rata-rata −1,09%/transaksi; dengan filter IHSG 395 transaksi, menang 31%, rata-rata −0,27%. Artinya aturan ini **belum terbukti untung** di pasar turun. Pantau dulu sebelum pakai modal penuh.
**Lot** dihitung agar: maks 1/3 modal per saham, dan rugi kalau kena stop ≤ 2% modal.
**Jual** bila: harga ≤ stop (awal −2×ATR, maks −7%, lalu naik mengikuti harga), target +15%, tutup di bawah MA50 saat rugi, atau 20 hari bursa tanpa hasil (prediksi salah).
Semua angka bisa diubah di `bot/config.py`. Segitiga hijau/merah di chart = hasil aturan yang sama diuji di data 1 tahun terakhir.

## Pasang (sekali saja, ±15 menit)

1. **Bot Telegram**: chat `@BotFather` → `/newbot` → simpan *token*. Kirim pesan apa saja ke bot Anda, lalu buka
   `https://api.telegram.org/bot<TOKEN>/getUpdates` dan catat `chat.id`.
2. **Claude API key**: buat di console.anthropic.com.
3. **GitHub**: buat repo baru, upload semua file ini.
   - Settings → Secrets and variables → Actions → **Secrets**: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `ANTHROPIC_API_KEY`
   - Settings → Pages → Source: *Deploy from branch* → `main` / `/docs`
   - (opsional) **Variables**: `DASHBOARD_URL` = alamat Pages Anda
4. Tab **Actions** → *Laporan harian 16:30 WIB* → **Run workflow** (centang *force*) untuk uji coba pertama.

Catatan: GitHub Pages gratis hanya untuk repo **publik** — artinya data posisi Anda bisa dilihat orang. Kalau mau privat, pakai GitHub Pro atau sambungkan repo privat ke Cloudflare Pages (gratis).
Jadwal GitHub Actions kadang telat 5-30 menit; data Yahoo Finance tertunda ±15 menit.

## Coba di komputer sendiri

```
pip install -r requirements.txt
python bot/daily.py --force
python -m http.server -d docs 8000   # buka http://localhost:8000
```

> Alat bantu analisis teknikal, bukan nasihat investasi. Sinyal bisa salah; selalu gunakan stop loss dan uang yang siap Anda tanggung risikonya.
