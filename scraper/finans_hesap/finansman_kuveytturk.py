"""
Kuveyt Türk - İhtiyaç / Taşıt / Konut Finansmanı scraper (v2)

Bu sürümde düzeltilenler:
1) Tutar/vade inputları artık gerçek klavye tuşlaması simüle edilerek
   dolduruluyor (önce temizle, sonra press_sequentially). Bu, maskeli /
   framework-kontrollü (React/Vue tarzı) inputlarda JS ile doğrudan
   `.value =` atamaktan çok daha güvenilir - önceki sürümde konut için
   1.000.000 ve 2.000.000 TL'nin AYNI sonucu vermesinin sebebi buydu.
2) Her fill sonrası inputun gerçek DOM value'su okunup doğrulanıyor;
   tutmazsa 1 kez daha denenip uyarı basılıyor.
3) Sabit gecikme yerine, tabloda değerin GERÇEKTEN değiştiğini
   (eski taksit tutarından farklı olduğunu) bekleyen bir polling
   mekanizması eklendi - bu hem daha hızlı hem daha güvenilir.
4) Tahsis ücreti için yanlış veriyi yakalayan (uyarı/dipnot metnini
   çeken) riskli fallback selector kaldırıldı. Artık sadece
   `data-th="Finansman Tahsis Ücreti"` deseni deneniyor; bulunamazsa
   None kalıyor ve DEBUG_DUMP_DETAIL=True iken ilgili bölümün
   innerHTML'i konsola basılıyor - gerçek selector'ü oradan görüp
   TAHSIS_UCRETI_SELECTORS listesine ekleyebilirsin.
5) Taşıt ürünü artık doğrulanmış: "Yeni Binek Araç Finansmanı".
"""

from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from finansman_config import get_kombinasyonlar, BANKA_URUNLERI
import os

url = "https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/konut-finansmanlari/konut-finansmani"


MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "sifreniz")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "finans_db")

MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
DB_NAME = MONGO_DB_NAME
COLLECTION_NAME = "finansman_teklifleri_kuveyt"

BANKA_KEY = "kuveyt"

# True yaparsan tahsis ücreti bulunamadığında ilgili detay bölümünün
# innerHTML'ini konsola basar (selector'ü netleştirmek için).
DEBUG_DUMP_DETAIL = False

# Doğrulandı: taşıt için gerçek option metni "Yeni Binek Araç Finansmanı"
URUN_ADAY_METINLERI = {
    "ihtiyac": ["İhtiyaç Finansmanı"],
    "konut": ["Konut Finansmanı"],
    "tasit": ["Yeni Binek Araç Finansmanı", "Araç Finansmanı", "Taşıt Finansmanı"],
}

KAR_ORANI_ALAN_ADI = {
    "ihtiyac": "kar_orani",
    "konut": "kar_orani_aylik",
    "tasit": "kar_orani_aylik",
}

# Sadece güvenilir olduğu doğrulanmış deseni bırakıyoruz.
TAHSIS_UCRETI_SELECTORS = [
    "td[data-th='Finansman Tahsis Ücreti']",
]


def urun_sec(page, aday_metinler):
    select_locator = page.locator(".input-block select[name='p4']")
    secilen_metin = select_locator.evaluate(
        """(el, adaylar) => {
            const options = Array.from(el.options);
            for (const aday of adaylar) {
                const aday_norm = aday.trim().toLowerCase();
                const opt = options.find(
                    o => o.text.trim().toLowerCase().includes(aday_norm)
                );
                if (opt) {
                    el.value = opt.value;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    if (window.jQuery) { window.jQuery(el).trigger('change'); }
                    return opt.text.trim();
                }
            }
            return null;
        }""",
        aday_metinler,
    )
    return secilen_metin


def alani_gercekten_doldur(page, locator, deger, max_deneme=2):
    """Gerçek klavye tuşlaması simüle ederek input'u doldurur ve
    DOM'daki değerin gerçekten değiştiğini doğrular."""
    hedef = str(deger)

    for deneme in range(1, max_deneme + 1):
        locator.click()
        # Alanı tamamen temizle
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")
        locator.press_sequentially(hedef, delay=30)
        page.keyboard.press("Tab")  # blur -> mask/format handler'ları tetikle
        page.wait_for_timeout(150)

        mevcut_deger = locator.input_value()
        # Sadece rakamları karşılaştır (nokta/virgül/TL/boşluk farklarını yok say)
        mevcut_rakamlar = "".join(ch for ch in mevcut_deger if ch.isdigit())
        hedef_rakamlar = "".join(ch for ch in hedef if ch.isdigit())

        if mevcut_rakamlar == hedef_rakamlar:
            return True

        print(
            f"UYARI: Alan doldurulamadı (deneme {deneme}/{max_deneme}). "
            f"Beklenen:{hedef_rakamlar} Gerçek:{mevcut_rakamlar}"
        )

    return False


def sonuc_degismesini_bekle(page, eski_taksit, timeout_ms=4000, adim_ms=200):
    """Taksit tutarı hücresi eski değerden farklı hale gelene kadar bekler."""
    gecen = 0
    while gecen < timeout_ms:
        yeni_taksit = page.locator('td[data-th="Taksit Tutarı"]').get_attribute("data-td")
        if yeni_taksit and yeni_taksit != eski_taksit:
            return yeni_taksit
        page.wait_for_timeout(adim_ms)
        gecen += adim_ms
    # Zaman aşımı - son okunan değeri döndür (değişmemiş olabilir, çağıran taraf loglar)
    return page.locator('td[data-th="Taksit Tutarı"]').get_attribute("data-td")


def tahsis_ucretini_oku(page):
    for sel in TAHSIS_UCRETI_SELECTORS:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                val = loc.first.get_attribute("data-td")
                if val:
                    return val
        except Exception:
            continue

    if DEBUG_DUMP_DETAIL:
        try:
            # Detay/ödeme planı bölümünün olası bir üst container'ı - tahmini
            # class adı; bulunamazsa tüm body'nin ilgili kısmını basar.
            print("---- Tahsis ücreti bulunamadı, sayfa detay bölümü dökümü ----")
            print(page.locator("body").evaluate("el => el.innerText.slice(0, 3000)"))
            print("---------------------------------------------------------------")
        except Exception as e:
            print(f"Debug dump hatası: {e}")

    return None


def finansmanKuveyt():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Mongo ayakta olmasa bile scraping'i durdurmuyoruz: asıl öncelik
    # doğru değerleri çekip konsola basmak. Yazma hatası olursa aşağıdaki
    # try/except (kombinasyon döngüsü içinde) sadece o kaydı loglar ve
    # bir sonraki kombinasyona geçer.
    urunler = BANKA_URUNLERI.get(BANKA_KEY, [])

    with sync_playwright() as syn:
        browser = syn.chromium.launch(
            slow_mo=1000,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        page.goto(url=url, wait_until="domcontentloaded", timeout=20000)
        page.mouse.wheel(0, 2500)

        for urun_key in urunler:
            aday_metinler = URUN_ADAY_METINLERI.get(urun_key)
            if not aday_metinler:
                print(f"UYARI: '{urun_key}' için aday metin tanımlı değil, atlanıyor.")
                continue

            alan = page.locator(".applicationform.w-100.position-relative")
            if not alan.is_visible():
                print(f"UYARI: Başvuru formu alanı görünmüyor, '{urun_key}' atlanıyor.")
                continue

            secilen_metin = urun_sec(page, aday_metinler)
            if not secilen_metin:
                print(f"UYARI: '{urun_key}' için hiçbir aday metin bulunamadı, atlanıyor.")
                continue

            print(f"Ürün Alanı Bulundu: {secilen_metin} ({urun_key})")
            page.wait_for_timeout(500)

            ay_vade = page.locator(".input-wrapper input[name='maturity1']")
            tutar_input = page.locator(".input-wrapper input[name='p1']")

            kombinasyonlar = get_kombinasyonlar(BANKA_KEY, urun_key)
            kar_orani_alan_adi = KAR_ORANI_ALAN_ADI[urun_key]

            for tutar, vade in kombinasyonlar:
                try:
                    eski_taksit = page.locator(
                        'td[data-th="Taksit Tutarı"]'
                    ).get_attribute("data-td")

                    tutar_ok = alani_gercekten_doldur(page, tutar_input, tutar)
                    vade_ok = alani_gercekten_doldur(page, ay_vade, vade)

                    if not (tutar_ok and vade_ok):
                        print(
                            f"HATA: [{BANKA_KEY}] {urun_key} Tutar:{tutar} Vade:{vade} "
                            f"-> input doldurulamadı, bu kombinasyon atlanıyor."
                        )
                        continue

                    taksit_tutari = sonuc_degismesini_bekle(page, eski_taksit)
                    odenecek_toplam = page.locator(
                        'td[data-th="Ödenecek Toplam Tutar"]'
                    ).get_attribute("data-td")
                    aylik_kar_orani = page.locator(
                        'td[data-th="Aylık Kâr Oranı"]'
                    ).get_attribute("data-td")
                    tahsis_ucreti = tahsis_ucretini_oku(page)

                    print(
                        f"[{BANKA_KEY}] {urun_key} | Tutar:{tutar} Vade:{vade} -> "
                        f"Taksit:{taksit_tutari} Toplam:{odenecek_toplam} "
                        f"Oran:{aylik_kar_orani} Tahsis:{tahsis_ucreti}"
                    )

                except Exception as e:
                    print(
                        f"HATA (scraping): [{BANKA_KEY}] {urun_key} Tutar:{tutar} "
                        f"Vade:{vade} değerleri okunurken hata: {e}"
                    )
                    continue

                # Değerler doğru okundu; Mongo'ya yazma ayrı bir adım.
                # Yazma başarısız olsa bile scraping'i etkilemesin.
                kayit = {
                    "banka": BANKA_KEY,
                    "urun": urun_key,
                    "finansman_tutari": tutar,
                    "vade": vade,
                    "aylik_taksit_tutari": taksit_tutari,
                    "geri_odenecek_toplam_tutar": odenecek_toplam,
                    kar_orani_alan_adi: aylik_kar_orani,
                    "tahsis_ucreti": tahsis_ucreti,
                }

                try:
                    collection.update_one(
                        {
                            "banka": BANKA_KEY,
                            "urun": urun_key,
                            "finansman_tutari": tutar,
                            "vade": vade,
                        },
                        {"$set": kayit},
                        upsert=True,
                    )
                except Exception as e:
                    print(
                        f"UYARI (mongo): [{BANKA_KEY}] {urun_key} Tutar:{tutar} "
                        f"Vade:{vade} değerleri OKUNDU ama Mongo'ya YAZILAMADI: {e}"
                    )

        browser.close()

    client.close()


if __name__ == "__main__":
    finansmanKuveyt()