"""
Albaraka Katılım - İhtiyaç / Taşıt / Konut Finansmanı Scraper
(Runner ile Tam Uyumlu ve MongoDB Entegreli Sürüm)
"""

import os
import re
from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from finansman_config import get_kombinasyonlar

# --- MONGODB BAĞLANTI AYARLARI ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

URL = "https://www.albaraka.com.tr/tr/hesaplama-araclari/finansman-hesaplama/konut-finansmani-hesaplama"
BANKA_KEY = "albaraka"

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

URUN_SECIMLERI = {
    "ihtiyac": {"projectparcode": "124", "isim": "İhtiyaç Finansmanı Hesaplama"},
    "tasit":   {"projectparcode": "102", "isim": "Taşıt Finansmanı Hesaplama"},
    "konut":   {"projectparcode": "143", "isim": "Konut Finansmanı Hesaplama"},
}

# Alan adı standartlaşması (diğer bankalarla tam uyum için)
KAR_ORANI_ALAN_ADI = {
    "ihtiyac": "kar_orani",
    "konut": "kar_orani_aylik",
    "tasit": "kar_orani_aylik",
}


def secim_yap(page, projectparcode: str, isim: str) -> bool:
    """Select2 dropdown'ından projectparcode'a göre ürün seçer ve ilk hesaplama cevabını bekler."""
    select_locator = page.locator("#slcfinansmanTuru")
    
    try:
        with page.expect_response(
            lambda r: "getFinanceCalculate" in r.url and r.status == 200,
            timeout=8000
        ):
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
                return False
    except Exception:
        pass  # İlk yükleme yanıtı hızlı gelebilir
        
    page.wait_for_timeout(300)
    return True


def input_doldur_ve_hesaplat(page, tutar: int, vade: int) -> bool:
    """Tutar ve vade alanlarını doldurup Albaraka'nın AJAX hesaplama isteğini tetikler."""
    try:
        with page.expect_response(
            lambda r: "getFinanceCalculate" in r.url and r.status == 200,
            timeout=7000
        ):
            # Tutar alanını temizle ve yaz
            tutar_input = page.locator("#finansmanTutarInput")
            tutar_input.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            tutar_input.press_sequentially(str(tutar), delay=20)
            
            # Vade alanını temizle ve yaz
            vade_input = page.locator("#finansmanVadeInput")
            vade_input.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            vade_input.press_sequentially(str(vade), delay=20)
            
            # Keyup ve change tetikleyerek AJAX debounce'unu çalıştır
            vade_input.evaluate("""el => {
                if (window.jQuery) {
                    window.jQuery(el).trigger('keyup').trigger('change');
                }
            }""")
            
        page.wait_for_timeout(200)
        return True
    except Exception as e:
        print(f"HATA: Hesaplama yanıtı beklenirken zaman aşımı / hata: {e}")
        return False


def masraf_ayristir(tooltip_html: str) -> dict:
    """Tooltip içeriğinden masraf kalemlerini çıkarır."""
    if not tooltip_html:
        return {}
    satirlar = re.findall(
        r"<div class='col-9 m-0 p-0'>(.*?)</div>\s*"
        r"<div class='col-3 m-0 p-0 text-right'>(.*?)</div>",
        tooltip_html
    )
    return {etiket.strip(): deger.strip() for etiket, deger in satirlar}


def finansmanAlbaraka():
    """finansman_runner.py tarafından çağrılan ana fonksiyon."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    collection = db[COLLECTION_NAME]

    with sync_playwright() as syn:
        browser = syn.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        try:
            page.goto(url=URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)

            for urun_key, secim in URUN_SECIMLERI.items():
                kar_orani_alan = KAR_ORANI_ALAN_ADI[urun_key]
                print(f"--- [Albaraka] Ürün: {urun_key} ({secim['isim']}) ---")

                if not secim_yap(page, secim["projectparcode"], secim["isim"]):
                    continue

                kombinasyonlar = get_kombinasyonlar(BANKA_KEY, urun_key)

                for tutar, vade in kombinasyonlar:
                    try:
                        ok = input_doldur_ve_hesaplat(page, tutar, vade)
                        if not ok:
                            print(f"[{BANKA_KEY}] {urun_key} Tutar:{tutar} Vade:{vade} -> Hesaplanamadı, atlanıyor.")
                            continue

                        # Güncellenmiş sonuçları oku
                        taksit = page.locator(".MonthlyInstallmentAmount").inner_text().strip()
                        toplam = page.locator(".TotalAmountTobeRefunded").inner_text().strip()
                        yillik_maliyet = page.locator(".AnnualCostRate").inner_text().strip()
                        ucretler_toplami = page.locator(".TotalFees").inner_text().strip()
                        kar_orani = page.locator("#finansmanOranInput").input_value().strip()

                        tooltip = page.locator("#toplam_masraf_info").get_attribute("data-original-title") or ""
                        masraflar = masraf_ayristir(tooltip)
                        tahsis_ucreti = next(
                            (v for k, v in masraflar.items() if "Tahsis Ücreti" in k),
                            None
                        )

                        print(
                            f"[{BANKA_KEY}] {urun_key} | Tutar:{tutar} Vade:{vade} -> "
                            f"Taksit:{taksit} Toplam:{toplam} Oran:{kar_orani} Tahsis:{tahsis_ucreti}"
                        )

                        belge = {
                            "banka": BANKA_KEY,
                            "urun": urun_key,
                            "urun_adi": secim["isim"],
                            "finansman_tutari": tutar,
                            "vade": vade,
                            "aylik_taksit_tutari": taksit,
                            "geri_odenecek_toplam_tutar": toplam,
                            kar_orani_alan: kar_orani,
                            "yillik_maliyet_orani": yillik_maliyet,
                            "tahsis_ucreti": tahsis_ucreti,
                            "ucretler_toplami": ucretler_toplami,
                            "masraf_detayi": masraflar,
                        }

                        try:
                            collection.insert_one(belge)
                        except Exception as e:
                            print(f"MongoDB yazma hatası: {e}")

                    except Exception as e:
                        print(f"HATA (scraping): [{BANKA_KEY}] {urun_key} Tutar:{tutar} Vade:{vade} -> {e}")
                        continue

        except Exception as e:
            print(f"Albaraka Katılım verileri çekilirken Hata: {e}")
        finally:
            browser.close()

    client.close()


if __name__ == "__main__":
    finansmanAlbaraka()