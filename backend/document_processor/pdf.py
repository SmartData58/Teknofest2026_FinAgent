"""PDF metin çıkarımı — ÖNCE METİN KATMANI, sonra OCR.

🚨 ÖNCEKİ DAVRANIŞ VE NEDEN DEĞİŞTİ
Eski sürüm HER sayfayı PNG'ye çevirip OCR modeline gönderiyordu. Bunun üç
ölçülmüş sonucu vardı:

 1) OCR modeli (baidu/Unlimited-OCR) bu ortamda HİÇ YÜKLENMİYOR:
      - transformers 5.15.1, modelin uzak kodunun beklediği
        `is_torch_fx_available` sembolünü artık sağlamıyor,
      - konteynerde CUDA yok (`torch.cuda.is_available() == False`) ama kod
        `.cuda()` çağırıyor.
    Sonuç: `process_image_with_ocr` her sayfa için
    "[HATA: OCR Motoru sistemde aktif değil!]" döndürüyordu — yani PDF
    yüklendiğinde kullanıcıya HİÇ METİN gitmiyordu.

 2) Buna rağmen log "✅ PDF başarıyla okundu" yazıyordu; hata sessiz kalıyordu.

 3) PDF'lerin büyük çoğunluğunda (banka kampanya belgeleri, oran tabloları,
    sözleşmeler) zaten GÖMÜLÜ METİN KATMANI var. PyMuPDF bunu doğrudan,
    kayıpsız ve modelsiz okuyabiliyor. Sayfayı görsele çevirip OCR'a vermek
    hem gereksiz hem de daha düşük kaliteli.

Yeni akış: her sayfa için önce `page.get_text()`. Metin katmanı varsa OCR'a
hiç gidilmez — model, GPU ve LLM görsel sınırı devreye girmez. Yalnızca
TARANMIŞ (metin katmanı olmayan) sayfalar OCR'a düşer.
"""
import os

import fitz
from loguru import logger

from ocr.unlimited import process_image_with_ocr

# Bir sayfanın "metin katmanı var" sayılması için gereken en az boşluksuz
# karakter. Kapak sayfalarında birkaç harf bulunabiliyor; eşik onları
# taranmış sayfa gibi ele alıp OCR'a göndermeyi engelliyor.
_ASGARI_METIN = 20

_OCR_HATA_ISARETI = "[HATA:"


def _sayfa_metni(sayfa) -> str:
    """Gömülü metin katmanını okur; yoksa boş dize döner."""
    try:
        return (sayfa.get_text() or "").strip()
    except Exception as e:
        logger.debug(f"Metin katmanı okunamadı: {e}")
        return ""


async def extract_text_from_pdf(file_path: str, progress_callback=None) -> str:
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    logger.info(f"📄 PDF işleniyor: {filename}")

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.error(f"PDF açılamadı ({file_path}): {e}")
        return "[PDF Okuma Hatası: Dosya açılamadı veya bozuk.]"

    parcalar = []
    metin_katmanli = 0
    ocr_denenen = 0
    ocr_basarisiz = 0

    try:
        for sayfa_no in range(len(doc)):
            sayfa = doc.load_page(sayfa_no)
            metin = _sayfa_metni(sayfa)

            if len(metin.replace(" ", "").replace("\n", "")) >= _ASGARI_METIN:
                # --- HIZLI YOL: gömülü metin katmanı ---
                metin_katmanli += 1
                if progress_callback:
                    await progress_callback(
                        f"📄 {filename} ({ext}) ➔ Sayfa {sayfa_no + 1}/{len(doc)} "
                        f"metin katmanından okundu..."
                    )
                parcalar.append(f"--- Sayfa {sayfa_no + 1} ---\n{metin}")
                continue

            # --- YEDEK YOL: taranmış sayfa, OCR gerekiyor ---
            ocr_denenen += 1
            if progress_callback:
                await progress_callback(
                    f"👁️ {filename} ({ext}) ➔ Sayfa {sayfa_no + 1}/{len(doc)} "
                    f"taranmış görünüyor, OCR deneniyor..."
                )

            gecici_png = f"{file_path}_page_{sayfa_no}.png"
            try:
                pix = sayfa.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                pix.save(gecici_png)
                ocr_metni = await process_image_with_ocr(gecici_png)
            except Exception as e:
                logger.error(f"Sayfa {sayfa_no + 1} OCR hatası: {e}")
                ocr_metni = f"{_OCR_HATA_ISARETI} OCR çalıştırılamadı]"
            finally:
                if os.path.exists(gecici_png):
                    os.remove(gecici_png)

            if ocr_metni.strip().startswith(_OCR_HATA_ISARETI):
                ocr_basarisiz += 1
                parcalar.append(
                    f"--- Sayfa {sayfa_no + 1} ---\n"
                    f"[Bu sayfa taranmış bir görsel ve OCR motoru bu ortamda "
                    f"etkin değil; sayfanın içeriği okunamadı.]"
                )
            else:
                parcalar.append(f"--- Sayfa {sayfa_no + 1} ---\n{ocr_metni}")
    finally:
        doc.close()

    sonuc = "\n\n".join(parcalar)

    # 🚨 Eskiden burada koşulsuz "✅ başarıyla okundu" yazılıyordu; hiç metin
    # çıkmadığında bile. Rapor artık gerçeği söylüyor.
    if metin_katmanli and not ocr_denenen:
        logger.success(f"✅ {filename}: {metin_katmanli} sayfa metin katmanından okundu (OCR gerekmedi).")
    elif metin_katmanli or (ocr_denenen and ocr_denenen > ocr_basarisiz):
        logger.success(
            f"✅ {filename}: {metin_katmanli} sayfa metin katmanından, "
            f"{ocr_denenen - ocr_basarisiz} sayfa OCR ile okundu "
            f"({ocr_basarisiz} sayfa okunamadı)."
        )
    else:
        logger.warning(
            f"⚠️ {filename}: hiçbir sayfadan metin çıkarılamadı "
            f"({ocr_denenen} sayfa taranmış ve OCR motoru etkin değil)."
        )
        return (
            "[PDF Okuma Uyarısı: Bu belgenin sayfalarında gömülü metin katmanı "
            "yok (taranmış görsel) ve OCR motoru bu ortamda etkin değil. "
            "Metin tabanlı bir PDF yükleyebilir ya da içeriği metin olarak "
            "yapıştırabilirsiniz.]"
        )

    return sonuc
