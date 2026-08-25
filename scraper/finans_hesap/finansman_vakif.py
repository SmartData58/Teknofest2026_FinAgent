from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from finansman_config import get_kombinasyonlar
import os

url = "https://www.vakifkatilim.com.tr/tr/yardimci-sayfalar/hesaplama-araclari/finansman-hesaplama"

# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")


DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)
COLLECTION_NAME = "finansman_urun"

BANKA_KEY = "vakif"

# Sayfadaki gerçek <option value="..."> -> bizim config'teki ürün anahtarı
# NOT: Vakıf'ta taşıt yok (BANKA_URUNLERI'nde de tanımlı değil), o yüzden
# BO / BO2 option'larını hiç işlemiyoruz.
URUN_ESLEME = {
    "IF": "ihtiyac",
    "K": "konut",     # Sıfır Konut Finansmanı
    "K2": "konut",    # 2. El Konut Finansmanı -- İSTERSEN ayrı urun_key
                       # olarak da tutabiliriz, şimdilik ikisi de "konut"
}


def finansmanVakif():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    collection = db[COLLECTION_NAME]

    with sync_playwright() as syn:
        browser = syn.chromium.launch(
            slow_mo=1500,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
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
            page.wait_for_timeout(500)

            # --- Config'ten bu ürün için tam kombinasyon listesi ---
            kombinasyonlar = get_kombinasyonlar(BANKA_KEY, urun_key)

            for tutar, vade in kombinasyonlar:
                tutar_input.fill(str(tutar))
                tutar_input.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                page.wait_for_timeout(400)

                # Vade select'inde bu değer gerçekten var mı kontrol edelim
                mevcut_vadeler = vade_select.locator("option").evaluate_all(
                    "opts => opts.map(o => o.value)"
                )
                if str(vade) not in mevcut_vadeler:
                    print(f"UYARI: Vade {vade} bu üründe mevcut değil, atlanıyor. "
                          f"(mevcut vadeler: {mevcut_vadeler[:5]}...)")
                    continue

                vade_select.select_option(value=str(vade))
                page.wait_for_timeout(600)

                taksit_tutari = page.locator("#installment-amount-el").inner_text()
                toplam_tutar = page.locator("#total-amount-el").inner_text()
                kar_orani = page.locator("#profit-rate-el").inner_text()
                ipotek_tesis_ucreti = page.locator("#mortgage-release-fee").inner_text()
                ekspertiz_ucreti = page.locator("#appraisement-fee-el").inner_text()

                print(f"[{BANKA_KEY}] {urun_key} | Tutar:{tutar} Vade:{vade} -> "
                      f"Taksit:{taksit_tutari} Toplam:{toplam_tutar} Oran:{kar_orani}")

                try:
                    collection.insert_one({
                        "banka": BANKA_KEY,
                        "urun_kodu": urun_value,
                        "urun": urun_key,
                        "finansman_tutari": tutar,
                        "vade": vade,
                        "aylik_taksit_tutari": taksit_tutari,
                        "geri_odenecek_toplam_tutar": toplam_tutar,
                        "kar_orani": kar_orani,
                        "tahsis_ucreti": None,  # Vakıf'ta bu isimle alan yok;
                                                 # en yakın karşılığı ipotek/ekspertiz aşağıda ayrı tutuldu
                        "ipotek_tesis_ucreti": ipotek_tesis_ucreti,
                        "ekspertiz_ucreti": ekspertiz_ucreti,
                    })
                except Exception as e:
                    print(f"MongoDB yazma hatası: {e}")

        browser.close()

    client.close()


if __name__ == "__main__":
    finansmanVakif()