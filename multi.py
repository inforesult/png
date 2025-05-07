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

def try_step(userid: str, label: str, step_func):
    try:
        step_func()
    except Exception as e:
        wib = datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M WIB")
        log_status("💥", f"Gagal saat {label}: {e}")
        kirim_telegram_log("GAGAL", f"<b>[GAGAL]</b>\n👤 {userid}\n❌ Gagal: {label}\n⌚ {wib}")
        raise

def run(playwright: Playwright, situs: str, userid: str, bet_raw: str, bet_raw2: str):
    wib = datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M WIB")
    log_status("📄", f"Mulai proses akun: {userid}")

    nomor_kombinasi = baca_file("config_png.txt")
    bet_kali = float(bet_raw)
    bet_kali2 = float(bet_raw2)
    jumlah_kombinasi = len(nomor_kombinasi.split('*'))

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/113.0 Safari/537.36"
    )
    page = context.new_page()

    try_step(userid, "Akses halaman utama", lambda: page.goto(f"https://{situs}/#/index?category=lottery"))

    try_step(userid, "Tutup popup", lambda: close_popup(page))

    def open_login():
        with page.expect_popup() as popup_info:
            page.get_by_role("heading", name="HOKI DRAW").click()
        nonlocal page1
        page1 = popup_info.value
    page1 = None
    try_step(userid, "Buka login HOKI DRAW", open_login)

    try_step(userid, "Isi form login", lambda: (
        page1.locator("input#loginUser").wait_for(),
        page1.locator("input#loginUser").type(userid, delay=100),
        page1.locator("input#loginPsw").type(pw, delay=120),
        page1.locator("div.login-btn").click()
    ))

    try_step(userid, "Klik 'Saya Setuju'", lambda: (
        page1.get_by_role("link", name="Saya Setuju").wait_for(timeout=10000),
        page1.get_by_role("link", name="Saya Setuju").click()
    ))

    try:
        saldo_text = page1.locator("span.overage-num").inner_text().strip()
        saldo_value = parse_saldo(saldo_text)
        log_status("💳", f"Saldo awal: Rp {saldo_value:,.0f}")
    except:
        saldo_value = 0.0

    try_step(userid, "Masuk halaman 5D Fast", lambda: page1.locator("a[data-urlkey='5dFast']").click())

    def klik_tombol_full():
        for _ in range(5):
            tombol = page1.get_by_text("FULL", exact=True)
            tombol.hover()
            time.sleep(random.uniform(0.8, 1.6))
            tombol.click()

    try_step(userid, "Klik tombol FULL", klik_tombol_full)

    try_step(userid, "Isi kombinasi & nominal", lambda: (
        page1.locator("#numinput").fill(nomor_kombinasi),
        page1.locator("input#buy3d").fill(""),
        page1.locator("input#buy3d").type(str(bet_kali), delay=80),
        page1.locator("input#buy4d").fill(""),
        page1.locator("input#buy4d").type(str(bet_kali2), delay=80),
        page1.locator("button.jq-bet-submit").click()
    ))

    try:
        page1.wait_for_selector("text=Bettingan anda berhasil dikirim.", timeout=15000)
        betting_berhasil = True
    except:
        betting_berhasil = False

    try:
        saldo_text = page1.locator("span.overage-num").inner_text().strip()
        saldo_value = parse_saldo(saldo_text)
    except:
        saldo_value = 0.0

    if betting_berhasil:
        pesan = f"<b>[SUKSES]</b>\n👤 {userid}\n💰 SALDO KAMU Rp. <b>{saldo_value:,.0f}</b>\n⌚ {wib}"
        kirim_telegram_log("SUKSES", pesan)
    else:
        pesan = f"<b>[GAGAL]</b>\n👤 {userid}\n💰 SALDO KAMU Rp. <b>{saldo_value:,.0f}</b>\n⌚ {wib}"
        kirim_telegram_log("GAGAL", pesan)

    context.close()
    browser.close()
    log_status("✅", f"Selesai proses akun {userid}.")

def close_popup(page):
    close_button = None
    try:
        close_button = page.get_by_role("img", name="close")
        if close_button.is_visible():
            time.sleep(0.5)
            close_button.click()
            log_status("✅", "Tombol close (by role) diklik.")
            return
    except:
        pass  # Jika gagal atau tidak ada, lanjut coba yang kedua

    try:
        close_button = page.locator("img.mask-close[alt='close']")
        if close_button.is_visible():
            time.sleep(0.5)
            close_button.click()
            log_status("✅", "Tombol close (by locator) diklik.")
    except:
        log_status("ℹ️", "Popup tidak muncul, lanjut ke step selanjutnya.")

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

            try:
                run(playwright, situs.strip(), userid.strip(), bet_raw.strip(), bet_raw2.strip())
            except:
                pass

if __name__ == "__main__":
    main()
