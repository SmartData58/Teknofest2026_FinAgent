import os
from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from finansman_config import get_kombinasyonlar

# --- MONGODB BAĞLANTI VE URL AYARLARI ---
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

url = os.getenv(
    "URL_FINANSMAN_VAKIF",
    "https://www.vakifkatilim.com.tr/tr/yardimci-sayfalar/hesaplama-araclari/finansman-hesaplama",
)

MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")


def _get_mongo_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    if MONGO_PASSWORD:
        return f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
    return f"mongodb://{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"


MONGO_URI = _get_mongo_uri()
COLLECTION_NAME = "finansman_urun"
BANKA_KEY = "vakif"

URUN_ESLEME = {
    "IF": "ihtiyac",
    "K": "konut",
    "K2": "konut",
}


def sonuc_degismesini_bekle(
    page, eski_taksit, timeout_ms=5000, adim_ms=200
) -> str:
    """Taksit alanının eski değerden farklılaşmasını (veya stabilleşmesini) bekler."""
    gecen = 0
    while gecen < timeout_ms:
        yeni_taksit = page.locator("#installment-amount-el").inner_text().strip()
        if yeni_taksit and yeni_taksit != eski_taksit:
            return yeni_taksit
        page.wait_for_timeout(adim_ms)
        gecen += adim_ms
    return page.locator("#installment-amount-el").inner_text().strip()


def finansmanVakif():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    collection = db[COLLECTION_NAME]

    with sync_playwright() as syn:
        browser = syn.chromium.launch(
            slow_mo=500,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        page.goto(url=url, wait_until="domcontentloaded", timeout=20000)
        page.mouse.wheel(0, 1500)

        form = page.locator("#financing-calculator")
        if not form.is_visible():
            print("Form bulunamadı, sayfa yapısı değişmiş olabilir.")
            browser.close()
            client.close()
            return

        urun_select = page.locator("#financing-type-select")
        tutar_input = page.locator("#financing-amount")
        vade_select = page.locator("#number-of-installments-select")

        for urun_value, urun_key in URUN_ESLEME.items():
            print(f"--- Ürün: {urun_value} ({urun_key}) ---")

            urun_select.select_option(value=urun_value)
            urun_select.evaluate(
                "el => el.dispatchEvent(new Event('change', { bubbles: true }))"
            )
            page.wait_for_timeout(500)

            kombinasyonlar = get_kombinasyonlar(BANKA_KEY, urun_key)

            for tutar, vade in kombinasyonlar:
                # 1. Eski taksit tutarını doldurma işleminden ÖNCE saklıyoruz
                eski_taksit = page.locator("#installment-amount-el").inner_text().strip()

                # 2. Tutarları klavye tuşlaması ile yazıyoruz
                tutar_input.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Delete")
                tutar_input.press_sequentially(str(tutar), delay=30)
                tutar_input.evaluate(
                    "el => el.dispatchEvent(new Event('change', { bubbles: true }))"
                )

                # 3. Vade varlığını kontrol edip seçiyoruz
                mevcut_vadeler = vade_select.locator("option").evaluate_all(
                    "opts => opts.map(o => o.value)"
                )
                if str(vade) not in mevcut_vadeler:
                    print(
                        f"UYARI: Vade {vade} bu üründe mevcut değil, atlanıyor. "
                        f"(mevcut vadeler: {mevcut_vadeler[:5]}...)"
                    )
                    continue

                vade_select.select_option(value=str(vade))
                vade_select.evaluate(
                    "el => el.dispatchEvent(new Event('change', { bubbles: true }))"
                )

                # 4. Sayfanın yeni hesaplamayı DOM'a yansıtmasını bekliyoruz
                taksit_tutari = sonuc_degismesini_bekle(page, eski_taksit)
                toplam_tutar = page.locator("#total-amount-el").inner_text().strip()
                kar_orani = page.locator("#profit-rate-el").inner_text().strip()
                ipotek_tesis_ucreti = page.locator("#mortgage-release-fee").inner_text().strip()
                ekspertiz_ucreti = page.locator("#appraisement-fee-el").inner_text().strip()

                print(
                    f"[{BANKA_KEY}] {urun_key} | Tutar:{tutar} Vade:{vade} -> "
                    f"Taksit:{taksit_tutari} Toplam:{toplam_tutar} Oran:{kar_orani}"
                )

                try:
                    collection.insert_one(
                        {
                            "banka": BANKA_KEY,
                            "urun_kodu": urun_value,
                            "urun": urun_key,
                            "finansman_tutari": tutar,
                            "vade": vade,
                            "aylik_taksit_tutari": taksit_tutari,
                            "geri_odenecek_toplam_tutar": toplam_tutar,
                            "kar_orani": kar_orani,
                            "tahsis_ucreti": None,
                            "ipotek_tesis_ucreti": ipotek_tesis_ucreti,
                            "ekspertiz_ucreti": ekspertiz_ucreti,
                        }
                    )
                except Exception as e:
                    print(f"MongoDB yazma hatası: {e}")

        browser.close()

    client.close()


if __name__ == "__main__":
    finansmanVakif()