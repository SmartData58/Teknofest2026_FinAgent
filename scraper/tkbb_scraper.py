import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import yaml

PROJE_KOK = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJE_KOK / "backend" / "configs" / "banks.yaml"

# Eşik Değerler (Milyar TL cinsinden)
BUYUK_ESIK = 500  # 500 Milyar TL ve üzeri -> büyük
ORTA_ESIK = 100   # 100 - 500 Milyar TL arası -> orta (altı küçük)

def tkbb_verilerini_cek_ve_siniflandir():
    """
    TKBB / Bilanço verilerini çekip bankaları büyüklük gruplarına ayırır
    ve banks.yaml dosyasını otomatik olarak günceller.
    """
    url = "https://www.tkbb.org.tr/veripetegi-detay/44"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print("🌐 TKBB Aktif Büyüklük verileri kontrol ediliyor...")

    # Güncel Aktif Büyüklükler (Milyar TL - Bilanço Verileri)
    # TKBB Veri Peteği istemci tarafında JS (Turboard) ile yüklendiği durumlarda 
    # fallback olarak güncel resmi finansal tablo verileri kullanılır.
    aktif_veri_map = {
        "kuveytturk": 1352.1,
        "vakif_katilim": 784.2,
        "ziraat_katilim": 768.8,
        "albaraka": 466.4,
        "emlak_katilim": 410.0,
        "turkiye_finans": 390.4,
        "dunya_katilim": 99.7,
        "hayat_finans": 25.2,
        "tom_katilim": 23.3,
        "adil_katilim": 0.0,
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, "html.parser")
            # HTML Tablo parse etme denemesi
            for tr in soup.select("table tr"):
                text = tr.text.lower()
                for banka_id in aktif_veri_map.keys():
                    if banka_id.replace("_", " ") in text:
                        rakamlar = re.findall(r"\d+[\.,]?\d*", text)
                        if rakamlar:
                            val = float(rakamlar[0].replace(".", "").replace(",", "."))
                            if val > 0:
                                aktif_veri_map[banka_id] = val
    except Exception as e:
        print(f"⚠️ TKBB canlı istek uyarısı (Varsayılan güncel veriler kullanılacak): {e}")

    # yaml dosyasını yükle ve güncelle
    if not CONFIG_PATH.exists():
        print(f"❌ Config dosyası bulunamadı: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    for banka in config.get("bankalar", []):
        b_id = banka["id"]
        aktif_val = aktif_veri_map.get(b_id, 0.0)

        if aktif_val >= BUYUK_ESIK:
            kategori = "büyük"
        elif aktif_val >= ORTA_ESIK:
            kategori = "orta"
        else:
            kategori = "küçük"

        banka["buyukluk_kategorisi"] = kategori
        banka["aktif_buyukluk_milyar_tl"] = aktif_val
        print(f"  -> [{b_id.upper()}] Aktif: {aktif_val} Milyar TL | Grup: {kategori}")

    # yaml dosyasını geri yaz
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)

    print("✅ banks.yaml dosyası büyüklük kategorileriyle güncellendi!")

if __name__ == "__main__":
    tkbb_verilerini_cek_ve_siniflandir()