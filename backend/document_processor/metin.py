"""Düz metin tabanlı belgeleri (.txt, .md, .csv, .tsv, .json, .log) okur.

🚨 NEDEN VAR: 500 promptluk koşuda `belge` kategorisinin TAMAMI şu cevabı aldı:

    "Yüklenen 'karma_kampanya_raporu.txt' dosyası sistem tarafından
     desteklenmediği için (.txt formatı şu an desteklenmiyor), belgenin
     içeriğine doğrudan erişimim bulunmamaktadır."

Yani belge analizi özelliği, en yaygın ve en kolay formatlar için hiç
çalışmıyordu: parser.py yalnızca Excel / görsel / PDF / Word tanıyordu.
Model bunu nazikçe açıklayıp veritabanına düşüyordu — bu yüzden testler
"geçmiş" görünüyordu, oysa ölçülmek istenen yetenek hiç denenmemişti.

TASARIM NOTLARI
  • KODLAMA TAHMİN EDİLMEZ, ÖLÇÜLÜR. Türkçe metinlerde en sık hata, UTF-8
    varsayıp Windows-1254/ISO-8859-9 kaydedilmiş bir dosyayı "KuveytÂ TÃ¼rk"
    diye okumaktır. Önce UTF-8 (BOM'lu/BOM'suz) deneniyor, olmazsa
    charset_normalizer ölçüyor, o da olmazsa cp1254'e düşülüyor.
  • BOYUT SINIRI VAR. Dosya içeriği doğrudan LLM promptuna giriyor; sınırsız
    okumak hem maliyeti hem gecikmeyi patlatır. Kesme yapıldığında bu AÇIKÇA
    metnin içine yazılıyor — sessizce yarısını atıp modeli eksik veriyle
    konuşturmak, yanlış cevaptan daha kötüdür çünkü fark edilmez.
  • CSV/TSV ham hâliyle bırakılıyor: sütun ayracı zaten metinde görünür ve
    model tabloyu okuyabiliyor. Ekstra ayrıştırma, kaçışlı alanlarda veri
    bozma riski taşır.
"""
import os

from loguru import logger

# Prompt'a girecek en fazla karakter. ~200 KB metin, llm-large'ın 262k token'lık
# bağlamında rahat sığar ama tek bir dosyanın bağlamı tamamen doldurmasını da
# engeller (kampanya verisine ve konuşma geçmişine yer kalmalı).
MAKS_KARAKTER = 200_000

DESTEKLENEN_UZANTILAR = (".txt", ".md", ".markdown", ".csv", ".tsv",
                         ".json", ".log", ".text")


def _coz(ham: bytes) -> str:
    """Bayt dizisini metne çevirir; kodlamayı tahmin etmek yerine ölçer."""
    for kodlama in ("utf-8-sig", "utf-8"):
        try:
            return ham.decode(kodlama)
        except UnicodeDecodeError:
            continue

    try:
        from charset_normalizer import from_bytes
        en_iyi = from_bytes(ham).best()
        if en_iyi is not None:
            logger.info(f"📄 Kodlama ölçüldü: {en_iyi.encoding}")
            return str(en_iyi)
    except Exception as e:                      # kütüphane yoksa/patlarsa
        logger.warning(f"charset_normalizer kullanılamadı: {e}")

    # Son çare: Türkçe Windows kodlaması. errors="replace" ile ASLA çökmez —
    # birkaç karakter bozulsa bile içeriğin tamamını kaybetmek daha kötü olur.
    return ham.decode("cp1254", errors="replace")


async def extract_text_from_plaintext(file_path: str) -> str:
    """Düz metin dosyasını okur ve prompt'a girecek hâle getirir."""
    ad = os.path.basename(file_path)
    logger.info(f"📄 Düz metin belgesi okunuyor: {ad}")

    try:
        with open(file_path, "rb") as f:
            ham = f.read()
    except OSError as e:
        logger.error(f"Düz metin dosyası açılamadı ({file_path}): {e}")
        return "[Hata: Dosya okunamadı]"

    if not ham.strip():
        return f"[Sistem Mesajı: '{ad}' dosyası boş.]"

    metin = _coz(ham).replace("\r\n", "\n").strip()

    if len(metin) > MAKS_KARAKTER:
        kirpilan = len(metin) - MAKS_KARAKTER
        metin = metin[:MAKS_KARAKTER] + (
            f"\n\n[Sistem Mesajı: '{ad}' dosyası {MAKS_KARAKTER:,} karakterde "
            f"KESİLDİ; {kirpilan:,} karakter okunmadı. Bu metne dayanan "
            f"toplam/sayım iddialarını 'gösterilen bölüm için' diye nitelendir.]"
        )
        logger.warning(f"📄 '{ad}' {kirpilan} karakter kırpıldı (sınır {MAKS_KARAKTER}).")

    logger.info(f"✅ Düz metin okundu: {ad} ({len(metin)} karakter)")
    return metin
