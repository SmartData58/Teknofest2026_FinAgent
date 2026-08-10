import os
from loguru import logger
from .excel import extract_text_from_excel
from .image import extract_text_from_image
from .pdf import extract_text_from_pdf
from .word import extract_text_from_word 

async def parse_document(file_path: str, progress_callback=None) -> str:
    if not os.path.exists(file_path):
        return ""

    # Dosya adını ve uzantısını ayırıyoruz
    filename = os.path.basename(file_path)
    file_ext = os.path.splitext(filename)[1].lower()
    
    logger.info(f"🔍 Belge ayrıştırılıyor: {filename} (Uzantı: {file_ext})")

    try:
        if file_ext in ['.xlsx', '.xls']:
            if progress_callback: await progress_callback(f"📊 {filename} ({file_ext}) ➔ Excel verileri çıkarılıyor...")
            return await extract_text_from_excel(file_path)
            
        elif file_ext in ['.png', '.jpg', '.jpeg']:
            if progress_callback: await progress_callback(f"👁️ {filename} ({file_ext}) ➔ Görsel OCR ile taranıyor...")
            return await extract_text_from_image(file_path)
            
        elif file_ext == '.pdf':
            # PDF kendi içinde sayfa sayfa bildirecek
            return await extract_text_from_pdf(file_path, progress_callback)
            
        elif file_ext in ['.doc', '.docx']:
            if progress_callback: await progress_callback(f"📝 {filename} ({file_ext}) ➔ Word belgesi okunuyor...")
            return await extract_text_from_word(file_path) 
            
        else:
            logger.warning(f"⚠️ Desteklenmeyen format: {file_ext}")
            return f"[Sistem Mesajı: {file_ext} formatı şu an desteklenmiyor.]"
            
    except Exception as e:
        logger.error(f"Ayrıştırma hatası ({file_path}): {str(e)}")
        return f"[Hata: Dosya okunamadı]"