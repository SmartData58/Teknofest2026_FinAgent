import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROJE_KOK = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJE_KOK / "backend" / "configs" / "banks.yaml"

BUYUK_ESIK = 500  # Milyar TL
ORTA_ESIK = 100   # Milyar TL

# Sayfadaki isimlerle yaml'daki id'leri eşleştirmek için map
BANKA_ISIM_MAP = {
    "kuveyttürk": "kuveytturk",
    "kuveyt türk": "kuveytturk",
    "vakıf katılım": "vakif_katilim",
    "ziraat katılım": "ziraat_katilim",
    "albaraka": "albaraka",
    "türkiye finans": "turkiye_finans",
    "emlak katılım": "emlak_katilim",
    "dünya katılım": "dunya_katilim",
    "hayat finans": "hayat_finans",
    "tom bank": "tom_katilim",
    "tom katılım": "tom_katilim",
    "adil katılım": "adil_katilim",
}

def tkbb_verilerini_playwright_ile_cek():
    url = os.getenv("URL_SCRAPER_TKBB", "https://tkbb.org.tr/veripetegi-detay/44")
    aktif_veri_map = {}

    print("🌐 Playwright ile TKBB Aktif Büyüklük verileri çekiliyor...")

    with sync_playwright() as p:
        # Chromium tarayıcısını başlatıyoruz
        browser = p.chromium.launch(headless=True)
        # Gerçek kullanıcı gibi görünmesi için viewport ve User-Agent veriyoruz
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Grafiğin tamamen render olması için 3 saniye ek bekleme
            page.wait_for_timeout(3000)

            # Ekrandaki tüm metin bloklarını (SVG/Div dâhil) alıyoruz
            page_text = page.content()
            
            # Alternatif olarak sayfa üzerindeki tüm visible text'leri alalım:
            inner_text = page.inner_text("body")
            lines = [line.strip() for line in inner_text.split("\n") if line.strip()]

            # Metinler arasından banka adı ve yanındaki/altındaki sayısal değerleri yakalama
            for i, line in enumerate(lines):
                line_lower = line.lower()
                for key_name, banka_id in BANKA_ISIM_MAP.items():
                    if key_name in line_lower:
                        # Banka adından sonraki ilk birkaç satırda sayı ara
                        for j in range(i, min(i + 5, len(lines))):
                            # Örn: 1.477.000 veya 888.924.872 gibi sayı formatlarını yakalar
                            rakamlar = re.findall(r"\d{1,3}(?:\.\d{3})+", lines[j])
                            if rakamlar:
                                # Binlik ayracı olan noktaları kaldırıp sayıya dönüştürüyoruz
                                # Sitede değerler "Bin TL" veya "TL" olabilir, bunu "Milyar TL"ye çeviriyoruz
                                ham_deger = float(rakamlar[0].replace(".", ""))
                                
                                # Eğer değer TL cinsindense (örn: 1.477.000.000) Milyar TL'ye bölüyoruz
                                if ham_deger > 100000:  # Bin TL cinsinden geliyorsa (örn: 888.924.872 Bin TL)
                                    milyar_val = round(ham_deger / 1000000, 2)
                                else:
                                    milyar_val = ham_deger
                                
                                aktif_veri_map[banka_id] = milyar_val
                                break

        except Exception as e:
            print(f"veri çekilirken hata oluştu: {e}")
        finally:
            browser.close()

    print(f"Çekilen Veriler: {aktif_veri_map}")

    # CONFIG UPDATE İŞLEMİ
    if not CONFIG_PATH.exists():
        print(f"Config dosyası bulunamadı: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    for banka in config.get("bankalar", []):
        b_id = banka["id"]
        # Eğer Playwright ile çekilemediyse mevcut değerini koru
        if b_id in aktif_veri_map:
            aktif_val = aktif_veri_map[b_id]
            
            if aktif_val >= BUYUK_ESIK:
                kategori = "Tier 1"
            elif aktif_val >= ORTA_ESIK:
                kategori = "Tier 2"
            else:
                kategori = "Tier 3"

            banka["buyukluk_kategorisi"] = kategori
            banka["aktif_buyukluk_milyar_tl"] = aktif_val
            print(f"  -> [{b_id.upper()}] Aktif: {aktif_val} Milyar TL | Grup: {kategori}")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)

    print("✅ banks.yaml başarıyla güncellendi!")

if __name__ == "__main__":
    tkbb_verilerini_playwright_ile_cek()