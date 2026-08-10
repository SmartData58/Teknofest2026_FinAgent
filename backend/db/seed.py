# =============================================================================
# db/seed.py — Başlangıç Verisi Yükleme (Seeding)
# =============================================================================

import yaml
from pathlib import Path

# backend. takılarını sildik ve PROJE_KOK importunu kaldırdık
from backend.db.database import get_session, init_db
from backend.db.models import Banka

# Docker konteyneri içinde ana dizinimizi (/app) kendimiz tanımlıyoruz
BASE_DIR = Path(__file__).resolve().parent.parent

# banks.yaml'daki bankaları veritabanına yükler/günceller
def seed_bankalar() -> None:

    # 1) YAML'ı oku. Dosya yolu doğrudan /app/configs/banks.yaml olarak güncellendi.
    with open(BASE_DIR / "configs" / "banks.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f) 

    with get_session() as session:
        for b in config["bankalar"]:
            # "Var mı?" kontrolü: kod alanına göre mevcut kaydı ara.
            mevcut = session.query(Banka).filter_by(kod=b["id"]).first()

            if mevcut:
                # Kayıt varsa alanlarını güncelle 
                mevcut.ad = b["ad"]
                mevcut.kisa_ad = b["kisa_ad"]
                mevcut.web_sitesi = b["web_sitesi"]
                mevcut.aktif = b["aktif"]
                print(f"  guncellendi : {b['id']}")
            else:
                # Yoksa yeni kayıt oluştur
                session.add(
                    Banka(
                        kod=b["id"],
                        ad=b["ad"],
                        kisa_ad=b["kisa_ad"],
                        web_sitesi=b["web_sitesi"],
                        aktif=b["aktif"],
                    )
                )
                print(f"  eklendi     : {b['id']}")

        # commit: yapılan tüm değişiklikleri kaydet
        session.commit()

        toplam = session.query(Banka).count()
        print(f"Toplam banka: {toplam}")

if __name__ == "__main__":
    
    print("Tablolar olusturuluyor...")
    init_db()
    print("Bankalar yukleniyor...")
    seed_bankalar()
    print("Tamamlandi.")