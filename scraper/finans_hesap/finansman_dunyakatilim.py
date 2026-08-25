"""
Dünya Katılım - İhtiyaç / Konut / Taşıt Finansmanı hesaplama scraper
(AJAX endpoint tabanlı)

Endpoint: POST https://dunyakatilim.com.tr/LoanCheckRate?lang=tr
Bu endpoint temiz bir JSON döndürüyor (monthlyInterest, totalPayment, rate) -
Ziraat'teki gibi HTML parse etmeye gerek yok.

ASP.NET Core CSRF (antiforgery) token: her sayfa yüklemesinde değişen bir
__RequestVerificationToken var, hem gizli bir form input'unda hem de eşleşen
bir cookie'de (.AspNetCore.Antiforgery.*) durur. Bu yüzden Playwright ile
sayfayı bir kez açıp token'ı DOM'dan okuyoruz; context cookie'yi otomatik
taşıyor. Token session boyunca geçerli kalmalı (tek kullanımlık değil gibi
görünüyor) ama garanti değil - sorun çıkarsa REFRESH_TOKEN_HER_N_ISTEK
değerini düşür.

KONUT VADE İSTİSNASI: "Konut Yeni" ürününde sitede 120 ay vade seçeneği
bulunmadığı için (min-max limitleri farklı), finansman_config.py'deki genel
120 ay değeri SADECE bu banka + konut kombinasyonu için 84 aya çevriliyor
(KONUT_VADE_OVERRIDE). finansman_config.py'ye dokunulmadı, diğer bankalar ve
diğer ürünler (ihtiyaç, taşıt) etkilenmiyor.

DOĞRULANMASI GEREKEN VARSAYIMLAR:
- KONUT: "Konut Yeni" (KONUTTUKETICI) mi "Konut 2.El" (2ELKONUTTUKETICI) mi
  kullanılmalı bilinmiyor - "Yeni" varsayıldı.
- TAŞIT: "Araç Binek Yeni" (ARACBINEKYENITUKETICI) varsayıldı, "2.El" değil.
- productCategory: sadece ihtiyaç için "ConsumerLoan" görüldü (gerçek curl'den).
  Konut/araç için "MortgageLoan"/"VehicleLoan" TAHMİN edildi - istek hata
  dönerse (result != "SUCCESS" veya HTTP hata) bu alanı doğru değerle
  güncellemen gerekir (o ürünü sitede seçip Hesapla'ya basıp yeni curl al).

TAHSİS ÜCRETİ: Bu response'ta hiç yer almıyor, None bırakıldı.
"""

import os
import json
from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from finansman_config import get_kombinasyonlar

# Herhangi bir finansman sayfası token/cookie almak için yeterli
HOMEPAGE_URL = "https://dunyakatilim.com.tr/kendim-icin/finansmanlar/ihtiyac-finansmani"
AJAX_URL = "https://dunyakatilim.com.tr/LoanCheckRate?lang=tr"

# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")


DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)
COLLECTION_NAME = "finansman_urun"

BANKA_KEY = "dunya_katilim"
URUNLER = ["ihtiyac", "konut", "tasit"]

# Ürün -> (productCode, productName, productCategory)
# productName/Category tam olarak sunucunun beklediği değerle eşleşmeli;
# eşleşmese de çoğu ASP.NET Core action'ı sadece productCode'a göre dallanır,
# ama garanti değil.
URUN_BILGISI = {
    "ihtiyac": {
        "productCode": "TUKETICIIHTIYAC",
        "productName": "Tüketici İhtiyaç Finansmanı",
        "productCategory": "ConsumerLoan",  # curl'den doğrulandı
    },
    "konut": {
        "productCode": "KONUTTUKETICI",  # "Konut Yeni" - VARSAYIM, "2ELKONUTTUKETICI" olabilir
        "productName": "Konut Yeni",
        "productCategory": "MortgageLoan",  # TAHMİN - doğrulanmadı
    },
    "tasit": {
        "productCode": "ARACBINEKYENITUKETICI",  # "Araç Binek Yeni" - VARSAYIM
        "productName": "Araç Binek Yeni",
        "productCategory": "VehicleLoan",  # TAHMİN - doğrulanmadı
    },
}

# ALINACAK_ALANLAR'a göre ihtiyaç için "kar_orani", konut/taşıt için
# "kar_orani_aylik" alan adı kullanılıyor.
KAR_ORANI_ALAN_ADI = {
    "ihtiyac": "kar_orani",
    "konut": "kar_orani_aylik",
    "tasit": "kar_orani_aylik",
}

# Sadece Dünya Katılım + konut için vade override'ı: sitede 120 ay yok,
# finansman_config.py'deki genel 120 ay değeri burada 84'e çevriliyor.
# Diğer bankalarda/ürünlerde bu override devreye girmiyor.
KONUT_VADE_OVERRIDE = 84


def tutar_formatla(tutar) -> str:
    """100000 -> '100.000' (Türkçe binlik ayraç formatı, sunucu bu formatı bekliyor)."""
    return f"{int(tutar):,}".replace(",", ".")


def urun_kombinasyonlarini_al(urun_key: str):
    """get_kombinasyonlar'dan gelen listeyi döndürür; konut için vadeyi
    120 -> KONUT_VADE_OVERRIDE (84) olacak şekilde yerel olarak değiştirir.
    finansman_config.py dosyasına dokunulmuyor, sadece bu script içindeki
    kombinasyon listesi düzeltiliyor."""
    kombinasyonlar = get_kombinasyonlar(BANKA_KEY, urun_key)

    if urun_key == "konut":
        kombinasyonlar = [
            (tutar, KONUT_VADE_OVERRIDE if vade == 120 else vade)
            for tutar, vade in kombinasyonlar
        ]

    return kombinasyonlar


def cerezli_context_al(syn):
    """Ana sayfayı açıp antiforgery cookie'sini + gizli form token'ını alır."""
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

    token = page.locator("input[name='__RequestVerificationToken']").first.input_value()
    if not token:
        print("UYARI: __RequestVerificationToken bulunamadı, istekler başarısız olabilir.")

    return browser, context, page, token


def finansman_hesapla_istegi(page, token: str, urun_bilgi: dict, tutar, vade: int):
    """LoanCheckRate endpoint'ine POST atar, JSON response döndürür (dict) ya da None."""
    form_data = {
        "productName": urun_bilgi["productName"],
        "productCode": urun_bilgi["productCode"],
        "productCategory": urun_bilgi["productCategory"],
        "amount": tutar_formatla(tutar),
        "installmentCount": str(vade),
        "userRate": "NaN",
        "userSelected": "false",  # banka kendi güncel oranını kullansın
        "__RequestVerificationToken": token,
    }
    response = page.request.post(
        AJAX_URL,
        form=form_data,
        headers={
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://dunyakatilim.com.tr",
            "referer": HOMEPAGE_URL,
            "x-requested-with": "XMLHttpRequest",
        },
    )
    if response.status != 200:
        print(f"UYARI: HTTP {response.status} - {response.text()[:300]}")
        return None
    try:
        return response.json()
    except Exception:
        print(f"UYARI: response JSON değil: {response.text()[:300]}")
        return None


def finansmanDunyaKatilim():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    collection = db[COLLECTION_NAME]

    with sync_playwright() as syn:
        browser, context, page, token = cerezli_context_al(syn)

        for urun_key in URUNLER:
            urun_bilgi = URUN_BILGISI[urun_key]
            kar_orani_alan = KAR_ORANI_ALAN_ADI[urun_key]
            kombinasyonlar = urun_kombinasyonlarini_al(urun_key)

            print(f"=== Ürün: {urun_key} ({urun_bilgi['productName']}) ===")

            for tutar, vade in kombinasyonlar:
                print(f"--- {urun_key} | Tutar:{tutar} Vade:{vade} ---")

                sonuc_json = finansman_hesapla_istegi(page, token, urun_bilgi, tutar, vade)
                if sonuc_json is None:
                    continue

                if sonuc_json.get("result") != "SUCCESS":
                    print(f"UYARI: result={sonuc_json.get('result')} - "
                          f"muhtemelen productCode/productCategory yanlış ya da "
                          f"tutar/vade bu ürünün limitleri dışında. Ham cevap: {sonuc_json}")
                    continue

                taksit = sonuc_json.get("monthlyInterest")
                toplam = sonuc_json.get("totalPayment")
                kar_orani = sonuc_json.get("rate")

                print(f"[{BANKA_KEY}] {urun_key} | Tutar:{tutar} Vade:{vade} -> "
                      f"Taksit:{taksit} Toplam:{toplam} Oran:{kar_orani}")

                belge = {
                    "banka": BANKA_KEY,
                    "urun": urun_key,
                    "finansman_tutari": tutar,
                    "vade": vade,
                    "aylik_taksit_tutari": taksit,
                    "geri_odenecek_toplam_tutar": toplam,
                    kar_orani_alan: kar_orani,
                    "tahsis_ucreti": None,  # bu response'ta yer almıyor
                }

                try:
                    collection.insert_one(belge)
                except Exception as e:
                    print(f"MongoDB yazma hatası: {e}")

                page.wait_for_timeout(400)  # sunucuyu yormamak için kısa bekleme

        browser.close()

    client.close()


if __name__ == "__main__":
    finansmanDunyaKatilim()