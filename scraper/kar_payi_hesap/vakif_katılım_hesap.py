from playwright.sync_api import sync_playwright

URL = "https://www.vakifkatilim.com.tr/tr/yardimci-sayfalar/hesaplama-araclari/kar-payi-hesaplama"

VADE_LABEL = "Aylık"  # 32 gün / 1 Ay karşılığı
TUTARLAR = ["100000", "250000"]


def vakif_hesapla(page, tutar, vade_label):
    eski_net_kar = page.locator("#dividend-net-profit-el").inner_text().strip()

    # Tutar'ı gir
    tutar_input = page.locator("#dividend-amount")
    tutar_input.click()
    tutar_input.fill("")
    tutar_input.type(tutar, delay=50)
    tutar_input.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
    tutar_input.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
    tutar_input.blur()
    page.wait_for_timeout(300)

    girilen_deger = tutar_input.input_value()

    # Vade'yi seç (native select)
    page.select_option("#dividend-expiry-select", label=vade_label)
    page.wait_for_timeout(300)

    # Sonucun değişmesini bekle
    try:
        page.wait_for_function(
            """(eski) => {
                const el = document.querySelector('#dividend-net-profit-el');
                return el && el.textContent.trim() !== eski && el.textContent.trim() !== '';
            }""",
            arg=eski_net_kar,
            timeout=5000
        )
    except Exception:
        pass

    page.wait_for_timeout(300)

    brut_kar = page.locator("#dividend-gross-profit-el").inner_text().strip()
    brut_oran = page.locator("#dividend-gross-rate-el").inner_text().strip()
    net_kar = page.locator("#dividend-net-profit-el").inner_text().strip()
    net_oran = page.locator("#dividend-net-rate-el").inner_text().strip()

    # Yatırılan tutar + Net kâr
    try:
        net_kar_sayi = float(
            net_kar.replace("TL", "").replace(".", "").replace(",", ".").strip()
        )
        toplam = float(tutar) + net_kar_sayi
        toplam_str = f"{toplam:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " TL"
    except ValueError:
        toplam_str = "hesaplanamadı"

    return {
        "banka": "Vakıf Katılım",
        "yatirilan_tutar": girilen_deger,
        "vade": "32 gün / 1 Ay",
        "brut_kar": brut_kar,
        "brut_oran": brut_oran,
        "net_kar": net_kar,
        "net_oran": net_oran,
        "toplam": toplam_str,
    }


def run():
    """Vakıf Katılım hesaplamalarını çalıştırır ve sonuç listesini döndürür."""
    sonuclar = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")

        try:
            page.click("#cookie-accept-btn", timeout=3000)
        except Exception:
            pass

        page.wait_for_selector("#dividend-calculator")
        page.wait_for_timeout(500)

        for tutar in TUTARLAR:
            sonuc = vakif_hesapla(page, tutar, VADE_LABEL)
            sonuclar.append(sonuc)

        browser.close()

    return sonuclar


def main():
    sonuclar = run()
    print("=" * 50)
    for s in sonuclar:
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