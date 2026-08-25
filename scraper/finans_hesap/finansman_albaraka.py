from playwright.sync_api import sync_playwright
from pymongo import MongoClient
import re
import os
from finansman_config import get_kombinasyonlar

url = "https://www.albaraka.com.tr/tr/hesaplama-araclari/finansman-hesaplama/konut-finansmani-hesaplama"

# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")


DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)
COLLECTION_NAME = "finansman_urun"

BANKA_KEY = "albaraka"

# projectparcode -> (urun_key, görünen isim)
# NOT: Albaraka'da genel "İhtiyaç Finansmanı" yok, en yakın karşılığı seçildi.
# Bunu onaylaman/değiştirmen gerekebilir.
URUN_SECIMLERI = {
    "ihtiyac": {"projectparcode": "124", "isim": "DİĞER TEKNOLOJİ FİNANSMANI"},
    "tasit":   {"projectparcode": "102", "isim": "SIFIR KM TAŞIT FİNANSMANI"},
    "konut":   {"projectparcode": "143", "isim": "İLK EVİM KONUT FİNANSMANI"},
}


def secim_yap(page, projectparcode: str, isim: str) -> bool:
    """Select2 dropdown'ından projectparcode'a göre ürün seçer."""
    select_locator = page.locator("#slcfinansmanTuru")
    basarili = select_locator.evaluate(
        """(el, ppc) => {
            const opt = Array.from(el.options).find(
                o => o.getAttribute('projectparcode') === ppc
            );
            if (!opt) return false;
            el.value = opt.value;
            el.dispatchEvent(new Event('change', { bubbles: true }));
            if (window.jQuery) {
                window.jQuery(el).trigger('change').trigger('change.select2');
            }
            return true;
        }""",
        projectparcode
    )
    if not basarili:
        print(f"UYARI: projectparcode={projectparcode} ({isim}) bulunamadı.")
    return basarili


def deger_gir(page, input_id: str, deger):
    """Tutar/Vade input'una değer yazar ve hesaplamayı tetikler."""
    inp = page.locator(f"#{input_id}")
    inp.fill(str(deger))
    inp.evaluate("el => { el.dispatchEvent(new Event('input', {bubbles:true})); "
                  "el.dispatchEvent(new Event('change', {bubbles:true})); "
                  "el.dispatchEvent(new KeyboardEvent('keyup', {bubbles:true})); }")


def masraf_ayristir(tooltip_html: str) -> dict:
    """#toplam_masraf_info tooltip'inin data-original-title içeriğinden
    (Tahsis Ücreti, Ekspertiz Masrafı, İpotek Tesis Ücreti gibi) kalemleri çıkarır."""
    if not tooltip_html:
        return {}
    satirlar = re.findall(
        r"<div class='col-9 m-0 p-0'>(.*?)</div>\s*"
        r"<div class='col-3 m-0 p-0 text-right'>(.*?)</div>",
        tooltip_html
    )
    return {etiket.strip(): deger.strip() for etiket, deger in satirlar}


def finansmanAlbaraka():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    collection = db[COLLECTION_NAME]

    with sync_playwright() as syn:
        browser = syn.chromium.launch(
            slow_mo=1000,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        page.goto(url=url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        for urun_key, secim in URUN_SECIMLERI.items():
            print(f"--- Ürün: {urun_key} ({secim['isim']}) ---")

            if not secim_yap(page, secim["projectparcode"], secim["isim"]):
                continue
            page.wait_for_timeout(800)

            kombinasyonlar = get_kombinasyonlar(BANKA_KEY, urun_key)

            for tutar, vade in kombinasyonlar:
                deger_gir(page, "finansmanTutarInput", tutar)
                page.wait_for_timeout(300)
                deger_gir(page, "finansmanVadeInput", vade)
                page.wait_for_timeout(1000)  # AJAX hesaplamasının dönmesi için bekle

                taksit = page.locator(".MonthlyInstallmentAmount").inner_text()
                toplam = page.locator(".TotalAmountTobeRefunded").inner_text()
                yillik_maliyet = page.locator(".AnnualCostRate").inner_text()
                ucretler_toplami = page.locator(".TotalFees").inner_text()
                kar_orani = page.locator("#finansmanOranInput").input_value()

                # Tooltip'ten tahsis ücreti / ekspertiz / ipotek kalemlerini ayrıştır
                tooltip = page.locator("#toplam_masraf_info").get_attribute("data-original-title")
                masraflar = masraf_ayristir(tooltip)
                tahsis_ucreti = next(
                    (v for k, v in masraflar.items() if "Tahsis Ücreti" in k),
                    None
                )

                print(f"[{BANKA_KEY}] {urun_key} | Tutar:{tutar} Vade:{vade} -> "
                      f"Taksit:{taksit} Toplam:{toplam} Oran:{kar_orani} "
                      f"Tahsis:{tahsis_ucreti} Masraflar:{masraflar}")

                try:
                    collection.insert_one({
                        "banka": BANKA_KEY,
                        "urun": urun_key,
                        "urun_adi_albaraka": secim["isim"],
                        "finansman_tutari": tutar,
                        "vade": vade,
                        "aylik_taksit_tutari": taksit,
                        "geri_odenecek_toplam_tutar": toplam,
                        "kar_orani": kar_orani,
                        "yillik_maliyet_orani": yillik_maliyet,
                        "tahsis_ucreti": tahsis_ucreti,
                        "ucretler_toplami": ucretler_toplami,
                        "masraf_detayi": masraflar,
                    })
                except Exception as e:
                    print(f"MongoDB yazma hatası: {e}")

        browser.close()

    client.close()


if __name__ == "__main__":
    finansmanAlbaraka()