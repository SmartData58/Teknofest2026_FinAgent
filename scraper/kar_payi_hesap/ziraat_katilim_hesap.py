from playwright.sync_api import sync_playwright

URL = "https://www.ziraatkatilim.com.tr/"

VADE_LABEL = "1 Ay Vadeli"
TUTARLAR = ["100000", "250000"]


def ziraat_hesapla(page, tutar, vade_label):
    # Tıklamadan önceki mevcut sonucu kaydet (değişimi tespit etmek için)
    eski_net_getiri = page.locator(".kar-payi-net-gelir").inner_text().strip()

    # Ana Para'yı gir
    ana_para = page.locator("#edit-kar-payi-ana-para")
    ana_para.click()
    ana_para.fill("")
    ana_para.type(tutar, delay=50)
    ana_para.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
    ana_para.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
    ana_para.blur()
    page.wait_for_timeout(300)

    girilen_deger = ana_para.input_value()

    # HESAPLA'ya tıkla
    page.locator("a.karpayi-hesapla").click()

    # Sonucun ESKİ değerden FARKLI bir değere değişmesini bekle
    try:
        page.wait_for_function(
            """(eski) => {
                const el = document.querySelector('.kar-payi-net-gelir');
                return el && el.textContent.trim() !== eski && el.textContent.trim() !== '';
            }""",
            arg=eski_net_getiri,
            timeout=6000
        )
    except Exception:
        print(f"Uyarı: {tutar} için sonuç zaman aşımında değişmedi, mevcut değer okunuyor.")

    net_getiri = page.locator(".kar-payi-net-gelir").inner_text().strip()
    brut_getiri = page.locator(".kar-payi-brut-gelir").inner_text().strip()
    net_oran = page.locator(".kar-payi-net-oran").inner_text().strip()
    brut_oran = page.locator(".kar-payi-brut-oran").inner_text().strip()

    return {
        "banka": "Ziraat Katılım",
        "yatirilan_tutar": girilen_deger,
        "vade": vade_label,
        "net_kar": net_getiri,
        "brut_getiri": brut_getiri,
        "net_oran": net_oran,
        "brut_oran": brut_oran,
    }


def run():
    """Ziraat Katılım hesaplamalarını çalıştırır ve sonuç listesini döndürür."""
    sonuclar = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")

        try:
            page.click("button.agree-button", timeout=3000)
        except Exception:
            pass

        page.get_by_role("tab", name="Kâr Payı  Hesaplama").click()
        page.wait_for_timeout(500)

        page.select_option("#edit-kar-payi-maturity-type", label=VADE_LABEL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)

        for tutar in TUTARLAR:
            sonuc = ziraat_hesapla(page, tutar, VADE_LABEL)
            sonuclar.append(sonuc)

        browser.close()

    return sonuclar


def main():
    sonuclar = run()
    print("=" * 50)
    for s in sonuclar:
        print(f"Yatırılan Tutar : {s['yatirilan_tutar']} TRY")
        print(f"Vade            : {s['vade']}")
        print(f"Net Kâr         : {s['net_kar']} TRY")
        print(f"Brüt Getiri     : {s['brut_getiri']} TRY")
        print(f"Net Oran        : {s['net_oran']} %")
        print(f"Brüt Oran       : {s['brut_oran']} %")
        print("-" * 50)


if __name__ == "__main__":
    main()