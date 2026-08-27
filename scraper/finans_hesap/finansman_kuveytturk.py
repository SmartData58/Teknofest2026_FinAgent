from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from finansman_config import get_kombinasyonlar
import os

# --- MONGODB BAĞLANTI VE URL AYARLARI ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

url = os.getenv("URL_FINANSMAN_KUVEYT", "https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/konut-finansmanlari/konut-finansmani")

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

BANKA_KEY = "kuveyt"

# Sayfadaki gerçek option metni -> bizim config'teki ürün anahtarı
URUN_ESLEME = {
    "İhtiyaç Finansmanı": "ihtiyac",
    "Taşıt Finansmanı": "tasit",   # NOT: sayfada bu isimle option yoktu,
                                    # gerçek isimleri (ör. "Yeni Binek Araç
                                    # Finansmanı") ile netleştirmemiz gerekiyor
    "Konut Finansmanı": "konut",
}


def finansmanKuveyt():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    collection = db[COLLECTION_NAME]

    with sync_playwright() as syn:
        browser = syn.chromium.launch(
            headless=True,
            slow_mo=2000,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        page.goto(url=url, wait_until="domcontentloaded", timeout=20000)
        page.mouse.wheel(0, 2500)

        for urun_metni, urun_key in URUN_ESLEME.items():
            alan = page.locator(".applicationform.w-100.position-relative")
            if not alan.is_visible():
                continue

            print(f"Ürün Alanı Bulundu: {urun_metni}")

            select_locator = page.locator(".input-block select[name='p4']")
            secim_basarili = select_locator.evaluate(
                """(el, aranan) => {
                    const aranan_norm = aranan.trim().toLowerCase();
                    const opt = Array.from(el.options).find(
                        o => o.text.trim().toLowerCase().includes(aranan_norm)
                    );
                    if (!opt) return false;
                    el.value = opt.value;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    if (window.jQuery) { window.jQuery(el).trigger('change'); }
                    return true;
                }""",
                urun_metni
            )
            if not secim_basarili:
                print(f"UYARI: '{urun_metni}' bulunamadı, atlanıyor.")
                continue

            page.wait_for_timeout(500)

            ay_vade = page.locator(".input-wrapper input[name='maturity1']")
            tutar_input = page.locator(".input-wrapper input[name='p1']")

            # --- Artık brute-force yerine config'ten gelen tam kombinasyonlar ---
            kombinasyonlar = get_kombinasyonlar(BANKA_KEY, urun_key)

            for tutar, vade in kombinasyonlar:
                tutar_input.fill(str(tutar))
                page.wait_for_timeout(300)
                ay_vade.fill(str(vade))
                page.wait_for_timeout(700)

                taksit_tutari = page.locator('td[data-th="Taksit Tutarı"]').get_attribute("data-td")
                odenecek_toplam = page.locator('td[data-th="Ödenecek Toplam Tutar"]').get_attribute("data-td")
                aylik_kar_orani = page.locator('td[data-th="Aylık Kâr Oranı"]').get_attribute("data-td")

                print(f"[{BANKA_KEY}] {urun_key} | Tutar:{tutar} Vade:{vade} -> "
                      f"Taksit:{taksit_tutari} Toplam:{odenecek_toplam} Oran:{aylik_kar_orani}")

                try:
                    collection.insert_one({
                        "banka": BANKA_KEY,
                        "urun": urun_key,
                        "finansman_tutari": tutar,
                        "vade": vade,
                        "aylik_taksit_tutari": taksit_tutari,
                        "geri_odenecek_toplam_tutar": odenecek_toplam,
                        "kar_orani": aylik_kar_orani,
                        "tahsis_ucreti": None,  # bu ekranda gösterilmiyor
                    })
                except Exception as e:
                    print(f"MongoDB yazma hatası: {e}")

        browser.close()

    client.close()


if __name__ == "__main__":
    finansmanKuveyt()