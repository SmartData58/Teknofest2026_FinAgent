import os
from playwright.sync_api import sync_playwright

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

URL = os.getenv("URL_KARPAYI_ALBARAKA", "https://www.albaraka.com.tr/tr/hesaplama-araclari/kar-payi-hesaplama")
TUTARLAR = ["100000", "250000"]
GUN_SAYISI = "32"


def albaraka_hesapla(page, tutar):
    # 1. Ana Para Girişi
    ana_para = page.locator("#karPayiYatirilanTutar")
    ana_para.click()
    ana_para.fill("")
    ana_para.type(str(tutar), delay=50)
    ana_para.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
    ana_para.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")

    # 2. Vade Türünü 'Gün' Yap
    page.locator('label[for="radioKarPayiGun"]').click()
    page.wait_for_timeout(300)

    # 3. Gün Sayısını Gir (32 Gün)
    gun_input = page.locator("#karPayiGun, input[name='karPayiGun']").first
    if gun_input.is_visible():
        gun_input.click()
        gun_input.fill("")
        gun_input.type(GUN_SAYISI, delay=50)
        gun_input.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
        gun_input.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
        gun_input.blur()

    # Hesaplamanın DOM'a yansımasını bekle
    page.wait_for_timeout(800)

    # 4. Görünür Olan Sonuç Değerlerini Çek
    brut_kar = page.locator(".GrossProfit:visible, p.total.GrossProfit:visible").last.inner_text().strip()
    brut_oran = page.locator(".GrossRate:visible, p.total.GrossRate:visible").last.inner_text().strip()
    net_kar = page.locator(".NetProfit:visible, .netProfit:visible").last.inner_text().strip()
    net_oran = page.locator(".NetRate:visible, .netRate:visible").last.inner_text().strip()

    # 5. Toplam Tutar Hesabı
    try:
        clean_net = (
            net_kar.replace("TRY", "")
            .replace("TL", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        toplam = float(tutar) + float(clean_net)
        toplam_str = f"{toplam:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " TL"
    except ValueError:
        toplam_str = "hesaplanamadı"

    return {
        "banka": "Albaraka Türk",
        "yatirilan_tutar": ana_para.input_value(),
        "vade": f"{GUN_SAYISI} Gün",
        "brut_kar": brut_kar,
        "brut_oran": brut_oran,
        "net_kar": net_kar,
        "net_oran": net_oran,
        "toplam": toplam_str,
    }


def run():
    """Albaraka Türk hesaplamalarını çalıştırır ve sonuç listesini döndürür."""
    sonuclar = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")

        # Çerez kapatma
        for selector in ["#cookie-accept-btn", ".efilli-banner-accept", "text=Kabul Et"]:
            try:
                page.click(selector, timeout=1500)
                break
            except Exception:
                pass

        page.wait_for_timeout(500)

        for tutar in TUTARLAR:
            sonuc = albaraka_hesapla(page, tutar)
            sonuclar.append(sonuc)

        browser.close()

    return sonuclar


def main():
    sonuclar = run()
    print("=" * 50)
    for s in sonuclar:
        print(f"Banka                    : {s.get('banka')}")
        print(f"Yatırılan Tutar          : {s['yatirilan_tutar']} TL")
        print(f"Vade                     : {s['vade']}")
        print(f"Brüt Kâr                 : {s['brut_kar']}")
        print(f"Brüt Oran                : {s['brut_oran']}")
        print(f"Net Kâr                  : {s['net_kar']}")
        print(f"Net Oran                 : {s['net_oran']}")
        print(f"Yatırılan Tutar + Net Kâr: {s['toplam']}")
        print("-" * 50)


if __name__ == "__main__":
    main()