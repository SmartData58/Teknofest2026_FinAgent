# DB Tabloları
# ORM: SQL kodu yazmak yerine python sınıfı olarak tanımlama tekniği
# ŞEMA TASARIM MANTIĞI (4 tablo)
# ------------------------------
#   bankalar ──1:N──▶ kampanyalar ──1:N──▶ cikarilan_alanlar
#   bankalar ──1:N──▶ scrape_log
#
# 1. bankalar         : BDDK listesindeki 10 katılım bankası (banks.yaml'dan)
# 2. kampanyalar      : Her kampanya metni + NLP'nin çıkardığı NORMALIZE alanlar
# 3. cikarilan_alanlar: Her alanın HAM hâli + hangi yöntemle çıkarıldığı + güven
#                       skoru. Neden ayrı tablo? AÇIKLANABİLİRLİK: jüri "bu %1,89
#                       nereden geldi?" diye sorduğunda "metindeki şu ifadeden,
#                       kural tabanlı yöntemle, %98 güvenle" diyebilmek için.
#                       (Değerlendirmede "model başarısı" %30 — kanıt gösterebilmek
#                       büyük avantaj.)
# 4. scrape_log       : Her veri çekme işleminin kaydı (ne zaman, kaç kampanya,
#                       hata var mı). Veri setinin tazeliğini kanıtlar ve site
#                       yapısı değişince hatayı hemen görmemizi sağlar.
# =============================================================================


from datetime import datetime, date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

#SQLAlchemy'nin SQL veri tiplerini ve kısıtlamalarını temsil eden yapıları projeye dahil edilir.
from sqlalchemy import (
    String,
    Text,
    Float,
    Integer,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    func,
    or_
    
)


class Base(DeclarativeBase):
    """
    Veritabanı tablolarının SQLAlchemy tarafından tanınmasını sağlayan ana sınıftır.
    Tüm modeller bu sınıftan miras alır.
    """
    
class Banka(Base):
    """
    BDDK listesindeki katılım bankası
    
    Kaynak: backend/confings/banks.ymal
    
    veritabanındaki bankalar tablosunun yapısı oluşturulur
    """
    
    __tablename__ = "bankalar"
    
    #PrimaryKey: her satırın benzersiz kimliği olur. autoincrement: otomatik arttırma
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    #
    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    ad: Mapped[str] = mapped_column(String(200))                #Bankanın Resmi Tam Adı
    kisa_ad: Mapped[str] = mapped_column(String(100))           #Arayüzde Görünen Ad
    web_sitesi: Mapped[str] = mapped_column(String(300))        #Banka URL
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)  #Bankanın Aktiflik Durumu
    
    #relationship: Python kodunda banka.kampanyalar veya banka.urunler denildiğinde 
    # o bankaya ait tüm kampanya veya ürün listesine doğrudan erişilmesini sağlar.
    kampanyalar: Mapped[list["Kampanya"]] = relationship(back_populates="banka")
    urunler: Mapped[list["Urun"]] = relationship(back_populates="banka")
    
class Kampanya(Base):
    """Bir kampanya metni ve NLP'nin çıkardığı NORMALİZE edilmiş alanlar.

    Kolon grupları şartnamenin 5.3 tablosuyla birebir eşleşir:
        - Finansman bilgileri: kâr payı, tutar, vade, taksit, masraflar
        - Kampanya bilgileri: tür, ödül, indirim, puan, süre, koşullar
        - Hedef kitle bilgileri
    NULL (None) = "metinde bu bilgi yok/bulunamadı" demektir. Örnek senaryodaki
    "Belirtilmemiş" durumu böyle temsil edilir — uydurma değer YAZILMAZ.
    """
        
    __tablename__ = "kampanyalar"
        
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        
    # ForeignKey: bu kampanyanın hangi bankaya ait olduğu (bankalar.id'ye işaret)
    banka_id: Mapped[int] = mapped_column(ForeignKey("bankalar.id"), index=True)
        
    # --- Kaynak bilgisi (veri nereden geldi — izlenebilirlik) ---------------
    url: Mapped[str] = mapped_column(String(500))
    baslik: Mapped[str | None] = mapped_column(String(300))   # | None = boş olabilir
    ham_metin: Mapped[str] = mapped_column(Text)              # Orijinal kampanya metni
    cekilme_tarihi: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
        # --- Sınıflandırma sonucu kampanya türü (şartname 5.4) --------------------------------
    # Değerler: finansman / ihtiyac_finansmani / konut_finansmani /
    #           tasit_finansmani / kart / alisveris_puani / yeni_musteri /
    #           yatirim_urunu 
    kampanya_turu: Mapped[str | None] = mapped_column(String(50), index=True)
    
    # --- Finansman bilgileri (şartname 5.3, normalize edilmiş) --------------
    kar_payi_orani: Mapped[float | None] = mapped_column(Float)   # %1,89 → 1.89
    finansman_tutari: Mapped[float | None] = mapped_column(Float) # TL cinsinden
    vade_ay: Mapped[int | None] = mapped_column(Integer)          # "10 yıl" → 120
    taksit_sayisi: Mapped[int | None] = mapped_column(Integer)
    tahsis_ucreti: Mapped[float | None] = mapped_column(Float)    # TL; 0.0 = masrafsız
    masraf_bilgisi: Mapped[str | None] = mapped_column(Text)      # Serbest metin özet

    # --- Kampanya bilgileri (şartname 5.3) -----------------------------------
    
    odul_miktari: Mapped[float | None] = mapped_column(Float)     # TL (5.000 TL çek → 5000)
    odul_aciklama: Mapped[str | None] = mapped_column(String(300))# "alışveriş çeki" vb.
    indirim_orani: Mapped[float | None] = mapped_column(Float)
    alisveris_puani: Mapped[float | None] = mapped_column(Float)
    baslangic_tarihi: Mapped[date | None] = mapped_column(Date)
    bitis_tarihi: Mapped[date | None] = mapped_column(Date)       # "31 Aralık 2026'ya kadar"
    kosullar: Mapped[str | None] = mapped_column(Text)
    
    # --- Hedef kitle (şartname 5.3) ------------------------------------------
    # Değerler: yeni_musteri / mevcut_musteri / maas_musterisi / segment / genel
    hedef_kitle: Mapped[str | None] = mapped_column(String(100), index=True)

    #Kampanyanın ait olduğu Banka nesnesine ve kampanya için üretilmiş 
    #CikarilanAlan (kanıt) kayıtlarına erişim sağlar.
    banka: Mapped["Banka"] = relationship(back_populates="kampanyalar")
    alanlar: Mapped[list["CikarilanAlan"]] = relationship(back_populates="kampanya")

    #Scraper tekrar çalıştığında aynı URL ve başlığa sahip aynı kayıtlar oluşmasını engeller.
    __table_args__ = (UniqueConstraint("url", "baslik", name="uq_kampanya_url_baslik"),)    
    
    #Geçerlilik Filtresi: Bitiş tarihi olmayan (sürekli) ya da bitiş tarihi bugünden sonra/bugüne eşit olan kampanyaları döndüren SQL filtre koşuludur.
    #Çağrıldığı andaki günün tarihini esas alır.
    def kampanya_gecerli_kosulu():
        return or_(Kampanya.bitis_tarihi.is_(None),
               Kampanya.bitis_tarihi >= date.today())
        
class Urun(Base):
    __tablename__ = "urunler"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    banka_id: Mapped[int] = mapped_column(ForeignKey("bankalar.id"), index=True)

    # --- Kaynak bilgisi (izlenebilirlik) -------------------------------------
    url: Mapped[str] = mapped_column(String(500))
    baslik: Mapped[str] = mapped_column(String(300))          # ürün adı
    ham_metin: Mapped[str] = mapped_column(Text)
    cekilme_tarihi: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    
    kategori: Mapped[str | None] = mapped_column(String(100))

    # Kampanya tarafıyla AYNI etiket kümesi (kampanya_turu ile eşleşir):
    # konut_finansmani / tasit_finansmani / ihtiyac_finansmani / finansman.
    # Aynı olması şart: chatbot "konut" sorusunu tek filtreyle iki tabloda da
    # arayabilsin diye (urun_turu_sorusu tek doğruluk kaynağı olarak kalır).
    urun_turu: Mapped[str | None] = mapped_column(String(50), index=True)

    # --- Ürünün ilan ettiği sayılar (hepsi NULL olabilir = "sayfada yok") ----
    azami_vade_ay: Mapped[int | None] = mapped_column(Integer)        # "120 aya kadar"
    azami_finansman_tutari: Mapped[float | None] = mapped_column(Float)
    # Teminat/ekspertiz değerine oranla azami finansman (%): konut ürününün
    # en ayırt edici sayısı. Kampanyada karşılığı YOK.
    azami_finansman_orani: Mapped[float | None] = mapped_column(Float)
    # Tahsis ücreti ORAN olarak (%0,5 → 0.5). Kampanyadaki tahsis_ucreti TL'dir;
    # aynı kolona yazmak iki farklı birimi tek yere doldurmak olurdu.
    tahsis_ucreti_orani: Mapped[float | None] = mapped_column(Float)
    # ÖRNEK ödeme planındaki kâr payı oranı. Adında "ornek" var çünkü ürün
    # sayfasındaki oran bir TEKLİF değil, örnek plan varsayımıdır — kampanya
    # oranıyla (ilan edilmiş, bağlayıcı) aynı kolonda durmamalı, cevapta da
    # "örnek plandaki oran" diye sunulur (uydurma yasağının devamı).
    ornek_kar_payi_orani: Mapped[float | None] = mapped_column(Float)
    masraf_bilgisi: Mapped[str | None] = mapped_column(Text)

    banka: Mapped["Banka"] = relationship(back_populates="urunler")
    alanlar: Mapped[list["CikarilanAlan"]] = relationship(back_populates="urun")

    # Ürünün kimliği URL'dir (kampanyadaki url+baslik ikilisinden farklı):
    # aynı ürün sayfasının başlığı sitede değişebilir, adresi kalıcıdır.
    __table_args__ = (UniqueConstraint("url", name="uq_urun_url"),)
    
 
class CikarilanAlan(Base):
    """Bir kampanya alanının çıkarım kaydı — AÇIKLANABİLİRLİK tablosu.

    Kampanya tablosundaki her normalize değerin "kanıtı" burada durur:
      alan_adi        : hangi alan (ör. "kar_payi_orani")
      ham_deger       : metindeki orijinal ifade (ör. "%1,89 kâr payı")
      normalize_deger : dönüştürülmüş hâli, metin olarak (ör. "1.89")
      yontem          : kural | ner | llm  → hangi çıkarım katmanı buldu
      guven_skoru     : 0.0–1.0 arası; kural=1.0 (deterministik),
                        NER/LLM model skorunu yazar
    Jüri sorusu "bu değer nereden geldi?" → bu tablo cevaptır. Ayrıca hibrit
    sistemde hangi yöntemin ne kadar başarılı olduğunu ölçmek için de kullanılır
    (dokümantasyondaki "model performans değerlendirmesi" bölümünü besler).
    """

    __tablename__ = "cikarilan_alanlar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Kanıt satırı ya bir kampanyaya ya bir ürüne aittir — ikisi de değil,
    # ikisi birden de değil (CheckConstraint bunu veritabanı seviyesinde
    # zorlar).
    kampanya_id: Mapped[int | None] = mapped_column(
        ForeignKey("kampanyalar.id"), index=True)
    urun_id: Mapped[int | None] = mapped_column(ForeignKey("urunler.id"), index=True)

    alan_adi: Mapped[str] = mapped_column(String(50), index=True)
    ham_deger: Mapped[str | None] = mapped_column(Text)
    normalize_deger: Mapped[str | None] = mapped_column(String(300))
    yontem: Mapped[str] = mapped_column(String(20))       # kural | ner | llm
    guven_skoru: Mapped[float] = mapped_column(Float, default=1.0)
    olusturma: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    kampanya: Mapped["Kampanya | None"] = relationship(back_populates="alanlar")
    urun: Mapped["Urun | None"] = relationship(back_populates="alanlar")

    __table_args__ = (
        CheckConstraint(
            "(kampanya_id IS NULL) <> (urun_id IS NULL)",
            name="ck_kanit_tek_kaynak"),
    )


class ScrapeLog(Base):
    """Her veri toplama çalışmasının kaydı.

    Neden var?
      1. Veri tazeliği kanıtı: "veri seti son X tarihinde güncellendi"
      2. Hata takibi: banka sitesi yapı değiştirince scraper kırılır —
         bu tablo hangi bankanın ne zaman hata verdiğini gösterir
      3. Dashboard'da "son güncelleme" bilgisi buradan okunur
    """

    __tablename__ = "scrape_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    banka_id: Mapped[int] = mapped_column(ForeignKey("bankalar.id"), index=True)
    baslama: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    durum: Mapped[str] = mapped_column(String(20))        # basarili | hata | kismi
    # kampanya | urun (34. adım): aynı banka artık iki AYRI koşuyla çekiliyor;
    # tür yazılmazsa "Kuveyt Türk 34 kayıt" satırının kampanya koşusu mu ürün
    # koşusu mu olduğu anlaşılmaz, tazelik takibi bozulurdu.
    kaynak_turu: Mapped[str] = mapped_column(
        String(20), default="kampanya", server_default="kampanya", index=True)
    # Koşuda çekilen kayıt sayısı. Eski adı kampanya_sayisi'ydi; ürün koşusu
    # eklenince ad yanıltıcı hâle geldi (ürün sayısını "kampanya_sayisi"
    # kolonunda tutmak, projedeki isimlendirme disiplinine aykırı olurdu).
    kampanya_sayisi: Mapped[int] = mapped_column(Integer, default=0)
    hata_mesaji: Mapped[str | None] = mapped_column(Text)