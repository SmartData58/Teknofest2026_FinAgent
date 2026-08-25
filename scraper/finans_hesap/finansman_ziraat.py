"""
Ziraat Katılım - İhtiyaç / Konut / Taşıt Finansmanı hesaplama scraper
(AJAX endpoint tabanlı)

Bu script, Ziraat Katılım'ın hesaplama formunu DOM üzerinden doldurmak yerine,
DevTools Network sekmesinden tespit edilen gerçek AJAX endpoint'ine
(POST /ajax/finansmanhesapla?_wrapper_format=drupal_ajax) doğrudan istek atar.

Playwright yine de kullanılıyor, ama SADECE geçerli çerezleri (TS... ile başlayan
bir bot-koruma/WAF çerezi var) almak için ana sayfayı bir kez açıyoruz.
Ardından page.request.post() ile aynı context'in çerezlerini kullanarak
doğrudan AJAX endpoint'ine istek atıyoruz.

ÖNEMLİ VARSAYIM (ilk çalıştırmada doğrula):
"Kâr Oranını Kendim Belirleyeceğim" işaretli değilken, payload'da hem
finans_kar_orani hem de finansman_is_bank_ratio=true gönderiliyor. Buradan yola
çıkarak, finansman_is_bank_ratio=true olduğunda sunucunun gönderilen
finans_kar_orani değerini YOK SAYIP kendi güncel bankacı oranını kullandığını
ve bunu yine "Kâr Oranı" alanında response'ta geri döndürdüğünü varsayıyoruz.

KONUT ÜRÜN SEÇİMİ: Dropdown'da hem "KONUT FINANSMANI KAMPANYA PAKETI"
(48671069) hem de "KONUT FINANSMANI (0-10.000.000 TL/1-120 AY)" (25961206)
var. Tablodaki 2.000.000 ve 1.000.000 tutarları "0-10.000.000 TL" aralığına
net şekilde uyduğu için genel ürünü (25961206) kullanıyoruz. Kampanya
paketinin farklı bir üst limiti olabilir; 2.000.000 için beklenmedik bir
sonuç/hata alırsan KONUT_FINANS_TYPE değerini 48671069 ile değiştirip dene.

TAŞIT: finansman_config.py'deki TASIT_800K_HESAPLANMAYAN_BANKALAR seti zaten
"ziraat"i içeriyor, yani get_kombinasyonlar("ziraat","tasit") otomatik olarak
800.000/36 kombinasyonunu ATLAR - ekstra bir filtre gerekmiyor.

TAHSİS ÜCRETİ: Bu AJAX response'unda hiç yer almıyor (muhtemelen "Ürün ve
Hizmet Ücretleri" sayfasında statik olarak duruyor). Bu script'te None
bırakıldı; ayrı bir statik kaynaktan doldurulması gerekiyor.
"""

import os
import re
import json
from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from finansman_config import get_kombinasyonlar

HOMEPAGE_URL = "https://www.ziraatkatilim.com.tr/"
AJAX_URL = "https://www.ziraatkatilim.com.tr/ajax/finansmanhesapla?_wrapper_format=drupal_ajax"

# NOT: Albaraka scriptindeki "${MONGO_USER:-admin}" gibi shell-stili syntax
# Python'da OTOMATIK expand OLMAZ (o kalıp sadece docker-compose/.env
# dosyalarında çalışır) - bu yüzden burada gerçek Python env-var okuma
# kullanıyoruz.
# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")


DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)
COLLECTION_NAME = "finansman_urun"

BANKA_KEY = "ziraat"
URUNLER = ["ihtiyac", "konut", "tasit"]

# DevTools > Elements'ten alınan gerçek <select id="edit-finansman-type"> option value'ları.
# Ürün -> {vade: finans_type_id}
FINANS_TYPE_MAP = {
    "ihtiyac": {
        12: "64356289",  # İHTİYAÇ FINANSMANI(1-12 AY)
        24: "64356288",  # İHTİYAÇ FINANSMANI (1-24 AY)
        36: "64356287",  # İHTİYAÇ FINANSMANI (1-36 AY)
    },
    "konut": {
        120: "25961206",  # KONUT FINANSMANI (0-10.000.000 TL/1-120 AY)
    },
    "tasit": {
        12: "59244341",  # TAŞIT FINANSMANI(1-12 AY)
        24: "65492134",  # TAŞIT FINANSMANI(1-24 AY)
        36: "64445628",  # TAŞIT FINANSMANI (1-36 AY)
        48: "64445629",  # TAŞIT FINANSMANI(1-48 AY)
    },
}

# ALINACAK_ALANLAR'a göre ihtiyaç için "kar_orani", konut/taşıt için
# "kar_orani_aylik" alan adı kullanılıyor - Mongo'ya bu isimle yazıyoruz.
KAR_ORANI_ALAN_ADI = {
    "ihtiyac": "kar_orani",
    "konut": "kar_orani_aylik",
    "tasit": "kar_orani_aylik",
}

# ajax_page_state[libraries] değeri - curl'den alındı. Bu değer sitenin CSS/JS
# derleme sürümüne bağlı olabilir; endpoint 400/500 dönerse önce bunu
# DevTools'tan güncel bir istekle tazelemeyi dene.
AJAX_PAGE_STATE_LIBRARIES = (
    "eJyNUY3O2zAIfCGreSQLO6ThCwEP2-3Spx_5mbpP2tRJln13HAhMgrzEpn7KkN44UlYJ6R_BrxqyGg4k"
    "DU2Ab18_Otp2m9TWMyKOgOmFAXvMqguhP2thAsk4_E2MI07QuQX82ZhkGUbrxWtfNDC8tmG_QgGDu0GZ"
    "62_PW7l1KT0x1RnHUJ4QK9qDvPpTbUEbLnqyULfacPXZKoYH4bMOx31bdeyM4bUMIKLdu1tRWt2F5Apa"
    "nDrzSevhS6z3_c3AuTM0_EZig3RkTyTHrEWtwVFgUvVP3NGMMJ5IvIdYmS56TTfFJ7U57ou4mzc1HjHT"
    "VRup_OE3Ssm356giWJ53dDXg2bJAfKAR-298Y9Fn8B0zJQPbdvOMFQrDCtE7yAxG5wB1Bfnge0v_U3UB"
    "K7DRBxcjVJL7B5eOvqzootAvzRUgew"
)


def cerezli_context_al(syn):
    """Ana sayfayı bir kez açıp WAF/bot-koruma çerezlerini toplayan bir
    Playwright context/page döndürür. Sonraki tüm AJAX istekleri bu context
    üzerinden (page.request ile) atılacak."""
    browser = syn.chromium.launch(
        headless=False,  # sorunsuz çalıştığını görünce True yapabilirsin
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
    )
    page = context.new_page()
    page.goto(HOMEPAGE_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1000)
    return browser, context, page


def finansman_hesapla_istegi(page, finans_type: str, tutar, vade: int):
    """AJAX endpoint'ine POST atar, ham response text'ini (JSON komut listesi) döndürür."""
    form_data = {
        "lang": "tr",
        "finansman_is_bank_ratio": "true",
        "finans_type": finans_type,
        "finans_kar_orani": "0",
        "finans_vade": str(vade),
        "finans_tutari": str(tutar),
        "_drupal_ajax": "1",
        "ajax_page_state[theme]": "zk",
        "ajax_page_state[theme_token]": "",
        "ajax_page_state[libraries]": AJAX_PAGE_STATE_LIBRARIES,
    }
    response = page.request.post(
        AJAX_URL,
        form=form_data,
        headers={
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://www.ziraatkatilim.com.tr",
            "referer": "https://www.ziraatkatilim.com.tr/",
            "x-requested-with": "XMLHttpRequest",
        },
    )
    if response.status != 200:
        print(f"UYARI: HTTP {response.status} - {response.text()[:300]}")
        return None
    return response.text()


def sonuc_ayristir(raw_text: str) -> dict:
    """Drupal AJAX komut listesinden taksit/toplam/kâr oranını çıkarır."""
    sonuc = {"taksit_tutari": None, "toplam_tutar": None, "kar_orani": None}
    try:
        komutlar = json.loads(raw_text)
    except json.JSONDecodeError:
        print("UYARI: Response JSON olarak parse edilemedi.")
        return sonuc

    for komut in komutlar:
        selector = komut.get("selector", "")
        data = komut.get("data", "")

        if selector == ".finansman-taksit-tutar":
            sonuc["taksit_tutari"] = data.strip()
        elif selector == ".finansman-toplam-tutar":
            sonuc["toplam_tutar"] = data.strip()
        elif selector == "#odeme-plani":
            # Kâr oranını özet tablosundan regex ile çek: <p>%2,89</p>
            m = re.search(r"K[âa]r Oran[ıi].*?<p>\s*%([\d.,]+)\s*</p>", data, re.DOTALL)
            if m:
                sonuc["kar_orani"] = m.group(1)

    return sonuc


def finansmanZiraat():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    collection = db[COLLECTION_NAME]

    with sync_playwright() as syn:
        browser, context, page = cerezli_context_al(syn)

        for urun_key in URUNLER:
            finans_type_map = FINANS_TYPE_MAP[urun_key]
            kar_orani_alan = KAR_ORANI_ALAN_ADI[urun_key]
            kombinasyonlar = get_kombinasyonlar(BANKA_KEY, urun_key)

            print(f"=== Ürün: {urun_key} ===")

            for tutar, vade in kombinasyonlar:
                finans_type = finans_type_map.get(vade)
                if not finans_type:
                    print(f"UYARI: {urun_key} için vade={vade} finans_type tanımlı değil, atlanıyor.")
                    continue

                print(f"--- {urun_key} | Tutar:{tutar} Vade:{vade} ---")

                raw = finansman_hesapla_istegi(page, finans_type, tutar, vade)
                if raw is None:
                    continue

                sonuc = sonuc_ayristir(raw)

                print(f"[{BANKA_KEY}] {urun_key} | Tutar:{tutar} Vade:{vade} -> "
                      f"Taksit:{sonuc['taksit_tutari']} Toplam:{sonuc['toplam_tutar']} "
                      f"Oran:{sonuc['kar_orani']}")

                belge = {
                    "banka": BANKA_KEY,
                    "urun": urun_key,
                    "finansman_tutari": tutar,
                    "vade": vade,
                    "aylik_taksit_tutari": sonuc["taksit_tutari"],
                    "geri_odenecek_toplam_tutar": sonuc["toplam_tutar"],
                    kar_orani_alan: sonuc["kar_orani"],
                    "tahsis_ucreti": None,  # bu AJAX response'unda yer almıyor
                }

                try:
                    collection.insert_one(belge)
                except Exception as e:
                    print(f"MongoDB yazma hatası: {e}")

                page.wait_for_timeout(400)  # sunucuyu yormamak için kısa bekleme

        browser.close()

    client.close()


if __name__ == "__main__":
    finansmanZiraat()