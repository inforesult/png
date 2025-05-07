import time
import random
import os
import requests
from playwright.sync_api import Playwright, sync_playwright, TimeoutError
from datetime import datetime
import pytz

pw = os.getenv("pw")
telegram_token = os.getenv("TELEGRAM_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

def log_status(emoji: str, message: str):
    print(f"{emoji} {message}")

def baca_file(file_name: str) -> str:
    with open(file_name, 'r') as file:
        return file.read().strip()

def kirim_telegram_log(status: str, pesan: str):
    print(pesan)
    if telegram_token and telegram_chat_id:
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                data={
                    "chat_id": telegram_chat_id,
                    "text": pesan,
                    "parse_mode": "HTML"
                }
            )
            if response.status_code != 200:
                print(f"Gagal kirim ke Telegram. Status: {response.status_code}")
                print(f"Respon Telegram: {response.text}")
        except Exception as e:
            print("Error saat mengirim ke Telegram:", e)

def parse_saldo(saldo_text: str) -> float:
    saldo_text = saldo_text.replace("Rp.", "").replace("Rp", "").strip().replace(",", "")
    return float(saldo_text)

def run(playwright: Playwright, situs: str, userid: str, bet_raw: str, bet_raw2: str):
    wib = datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M WIB")
    try:
        log_status("📄", f"Mulai proses akun: {userid}")
        nomor_kombinasi = baca_file("config_png.txt")
        bet_kali = float(bet_raw)
        bet_kali2 = float(bet_raw2)
        jumlah_kombinasi = len(nomor_kombinasi.split('*'))
        total_bet_rupiah = jumlah_kombinasi * (bet_kali + bet_kali2) * 1000

        log_status("🌐", f"Login ke situs {situs}...")
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/113.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(f"https://{situs}/#/index?category=lottery")

        try:
            log_status("❌", "Cek tombol close popup...")
            try:
                close_button = page.get_by_role("img", name="close")
                close_button.wait_for(state="visible", timeout=3000)
            except TimeoutError:
                close_button = page.locator("img.mask-close[alt='close']")
                close_button.wait_for(state="visible", timeout=3000)

            if close_button:
                time.sleep(0.5)
                close_button.click()
                log_status("✅", "Tombol close diklik.")
        except Exception:
            log_status("ℹ️", "Popup close tidak ditemukan. Lanjut.")

        log_status("➡️", "Buka popup login HOKI DRAW...")
        with page.expect_popup() as popup_info:
            page.get_by_role("heading", name="HOKI DRAW").click()
        page1 = popup_info.value

        log_status("🔐", "Isi form login...")
        page1.locator("input#loginUser").wait_for()
        page1.locator("input#loginUser").type(userid, delay=100)
        page1.locator("input#loginPsw").type(pw, delay=120)
        page1.locator("div.login-btn").click()

        try:
            page1.get_by_role("link", name="Saya Setuju").wait_for(timeout=10000)
            page1.get_by_role("link", name="Saya Setuju").click()
            log_status("✅", "Klik 'Saya Setuju'")
        except:
            log_status("ℹ️", "'Saya Setuju' tidak muncul")

        log_status("💰", "Cek saldo awal...")
        try:
            saldo_text = page1.locator("span.overage-num").inner_text().strip()
            saldo_value = parse_saldo(saldo_text)
            log_status("💳", f"Saldo awal: Rp {saldo_value:,.0f}")
        except:
            saldo_value = 0.0

        log_status("🎯", "Masuk halaman 5D Fast...")
        page1.locator("a[data-urlkey='5dFast']").click()
        for _ in range(5):
            tombol = page1.get_by_text("FULL", exact=True)
            tombol.hover()
            time.sleep(random.uniform(0.8, 1.6))
            tombol.click()

        log_status("✏️", "Isi kombinasi & nominal...")
        page1.locator("#numinput").fill(nomor_kombinasi)
        page1.locator("input#buy3d").fill("")
        page1.locator("input#buy3d").type(str(bet_kali), delay=80)
        page1.locator("input#buy4d").fill("")
        page1.locator("input#buy4d").type(str(bet_kali2), delay=80)
        page1.locator("button.jq-bet-submit").click()

        log_status("🕒", "Menunggu hasil taruhan...")
        try:
            page1.wait_for_selector("text=Bettingan anda berhasil dikirim.", timeout=15000)
            betting_berhasil = True
            log_status("🎉", "Taruhan berhasil dikirim.")
        except:
            betting_berhasil = False
            log_status("❌", "Taruhan gagal.")

        try:
            saldo_text = page1.locator("span.overage-num").inner_text().strip()
            saldo_value = parse_saldo(saldo_text)
        except:
            saldo_value = 0.0

        if betting_berhasil:
            pesan_sukses = (
                f"<b>[SUKSES]</b>\n"
                f"👤 {userid}\n"
                f"💰 SALDO KAMU Rp. <b>{saldo_value:,.0f}</b>\n"
                f"⌚ {wib}"
            )
            kirim_telegram_log("SUKSES", pesan_sukses)
        else:
            pesan_gagal = (
                f"<b>[GAGAL]</b>\n"
                f"👤 {userid}\n"
                f"💰 SALDO KAMU Rp. <b>{saldo_value:,.0f}</b>\n"
                f"⌚ {wib}"
            )
            kirim_telegram_log("GAGAL", pesan_gagal)

        context.close()
        browser.close()
        log_status("✅", f"Selesai proses akun {userid}.\n")

    except Exception as e:
        kirim_telegram_log("GAGAL", f"<b>[ERROR]</b>\n{userid}@{situs}\n❌ {str(e)}\n⌚ {wib}")
        log_status("💥", f"Error fatal untuk {userid}: {e}")

def main():
    log_status("🚀", "Memulai proses multi akun...")
    bets = baca_file("multi.txt").splitlines()
    with sync_playwright() as playwright:
        for baris in bets:
            if '|' not in baris or baris.strip().startswith("#"):
                continue
            parts = baris.strip().split('|')
            if len(parts) != 4:
                continue
            situs, userid, bet_raw, bet_raw2 = parts
            run(playwright, situs.strip(), userid.strip(), bet_raw.strip(), bet_raw2.strip())

if __name__ == "__main__":
    main()
