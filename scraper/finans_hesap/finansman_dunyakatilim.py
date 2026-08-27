"""
Dünya Katılım - İhtiyaç / Konut / Taşıt Finansmanı Scraper (Düzeltilmiş ve Stabil Sürüm)
"""

import os
import json
import requests
from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from finansman_config import get_kombinasyonlar

# --- MONGODB BAĞLANTI VE URL AYARLARI ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

HOMEPAGE_URL = os.getenv("URL_FINANSMAN_DUNYA_HOMEPAGE", "https://www.dunyakatilim.com.tr/kendim-icin/finansmanlar/ihtiyac-finansmani")
AJAX_URL = os.getenv("URL_FINANSMAN_DUNYA_AJAX", "https://www.dunyakatilim.com.tr/LoanCheckRate?lang=tr")

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
BANKA_KEY = "dunya_katilim"
URUNLER = ["ihtiyac", "konut", "tasit"]

# Doğrulanmış ürün parametreleri
URUN_BILGISI = {
    "ihtiyac": {
        "productCode": "TUKETICIIHTIYAC",
        "productName": "Tüketici İhtiyaç Finansmanı",
        "productCategory": "ConsumerLoan",
    },
    "konut": {
        "productCode": "KONUTTUKETICI",
        "productName": "Konut Yeni",
        "productCategory": "MortgageLoan",
    },
    "tasit": {
        "productCode": "ARACBINEKYENITUKETICI",
        "productName": "Araç Binek Yeni",
        "productCategory": "VehicleLoan",
    },
}

KAR_ORANI_ALAN_ADI = {
    "ihtiyac": "kar_orani",
    "konut": "kar_orani_aylik",
    "tasit": "kar_orani_aylik",
}

# Dünya Katılım konut finansmanında maksimum 84 ay vade desteklemektedir
KONUT_VADE_OVERRIDE = 84


def tutar_formatla(tutar) -> str:
    """100000 -> '100.000' (Türkçe binlik ayraç formatı)"""
    return f"{int(tutar):,}".replace(",", ".")


def urun_kombinasyonlarini_al(urun_key: str):
    kombinasyonlar = get_kombinasyonlar(BANKA_KEY, urun_key)
    if urun_key == "konut":
        kombinasyonlar = [
            (tutar, KONUT_VADE_OVERRIDE if vade == 120 else vade)
            for tutar, vade in kombinasyonlar
        ]
    return kombinasyonlar


def token_ve_cerezleri_al():
    """Playwright ile sayfayı açıp güncel cookie ve CSRF token'ı alır."""
    with sync_playwright() as syn:
        browser = syn.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        # networkidle yerine domcontentloaded kullanarak takılmaları önlüyoruz
        page.goto(HOMEPAGE_URL, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(1000)

        token = page.locator("input[name='__RequestVerificationToken']").first.input_value()
        cookies = {c["name"]: c["value"] for c in context.cookies()}

        browser.close()
        return token, cookies


def yeni_http_session_olustur():
    """Taze token ve çerezler ile yapılandırılmış bir requests.Session döndürür."""
    token, cookies = token_ve_cerezleri_al()
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "origin": "https://www.dunyakatilim.com.tr",
        "referer": HOMEPAGE_URL,
        "x-requested-with": "XMLHttpRequest",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })
    return session, token


def finansman_hesapla_istegi(session: requests.Session, token: str, urun_bilgi: dict, tutar, vade: int):
    """requests.Session üzerinden POST isteği atar."""
    form_data = {
        "productName": urun_bilgi["productName"],
        "productCode": urun_bilgi["productCode"],
        "productCategory": urun_bilgi["productCategory"],
        "amount": tutar_formatla(tutar),
        "installmentCount": str(vade),
        "userRate": "",
        "userSelected": "false",
        "__RequestVerificationToken": token,
    }

    try:
        response = session.post(AJAX_URL, data=form_data, timeout=10)
        if response.status_code != 200:
            print(f"UYARI: HTTP {response.status_code} - {response.text[:200]}")
            return None
        return response.json()
    except Exception as e:
        print(f"İstek hatası: {e}")
        return None


def run() -> list:
    """Modüler kullanım için dict listesi döndüren run() fonksiyonu."""
    sonuclar = []
    session, token = yeni_http_session_olustur()

    for urun_key in URUNLER:
        urun_bilgi = URUN_BILGISI[urun_key]
        kar_orani_alan = KAR_ORANI_ALAN_ADI[urun_key]
        kombinasyonlar = urun_kombinasyonlarini_al(urun_key)

        print(f"\n=== [Dünya Katılım] Ürün: {urun_key} ({urun_bilgi['productName']}) ===")

        for tutar, vade in kombinasyonlar:
            sonuc_json = finansman_hesapla_istegi(session, token, urun_bilgi, tutar, vade)
            
            # Token süresi bittiyse bir kez yenileyip tekrar dene
            if sonuc_json is None or sonuc_json.get("result") != "SUCCESS":
                session, token = yeni_http_session_olustur()
                sonuc_json = finansman_hesapla_istegi(session, token, urun_bilgi, tutar, vade)

            if not sonuc_json or sonuc_json.get("result") != "SUCCESS":
                print(f"HATA: [{BANKA_KEY}] {urun_key} Tutar:{tutar} Vade:{vade} hesaplanamadı. Yanıt: {sonuc_json}")
                continue

            taksit = sonuc_json.get("monthlyInterest")
            toplam = sonuc_json.get("totalPayment")
            kar_orani = sonuc_json.get("rate")

            print(
                f"[{BANKA_KEY}] {urun_key} | Tutar:{tutar} Vade:{vade} -> "
                f"Taksit:{taksit} TL Toplam:{toplam} TL Oran:%{kar_orani}"
            )

            sonuclar.append({
                "banka": BANKA_KEY,
                "urun": urun_key,
                "urun_adi": urun_bilgi["productName"],
                "finansman_tutari": tutar,
                "vade": vade,
                "aylik_taksit_tutari": f"{taksit:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."),
                "geri_odenecek_toplam_tutar": f"{toplam:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."),
                kar_orani_alan: str(kar_orani),
                "tahsis_ucreti": None,
            })

    session.close()
    return sonuclar


def finansmanDunyaKatilim():
    """MongoDB'ye yazma yapan ana fonksiyon."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    collection = db[COLLECTION_NAME]

    veriler = run()
    for veri in veriler:
        try:
            collection.insert_one(veri)
        except Exception as e:
            print(f"MongoDB yazma hatası: {e}")

    client.close()
    print(f"\nDünya Katılım: Toplam {len(veriler)} kayıt tamamlandı.")


if __name__ == "__main__":
    finansmanDunyaKatilim()