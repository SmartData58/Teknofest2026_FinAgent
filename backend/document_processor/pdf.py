import os
import fitz 
from loguru import logger
from ocr.unlimited import process_image_with_ocr

async def extract_text_from_pdf(file_path: str, progress_callback=None) -> str:
    logger.info(f"📄 PDF OCR işlemine alınıyor: {file_path}")
    
    # YENİ: Dosya adını ve uzantısını tam olarak yakalıyoruz
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    
    try:
        doc = fitz.open(file_path)
        full_text = []
        
        for page_num in range(len(doc)):
            # YENİ: Arayüze fırlatılacak çok detaylı, canlı durum mesajı
            status_msg = f"📄 {filename} ({ext}) ➔ Sayfa {page_num + 1}/{len(doc)} yapay zekaya okutuluyor..."
            logger.info(status_msg)
            
            if progress_callback:
                await progress_callback(status_msg)
                
            page = doc.load_page(page_num)
            zoom = 2.0 
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            temp_img_path = f"{file_path}_page_{page_num}.png"
            pix.save(temp_img_path)
            
            page_text = await process_image_with_ocr(temp_img_path)
            full_text.append(f"--- Sayfa {page_num + 1} ---\n{page_text}")
            
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
                
        logger.success(f"✅ PDF başarıyla okundu: {filename}")
        return "\n\n".join(full_text)
        
    except Exception as e:
        logger.error(f"PDF okuma hatası ({file_path}): {str(e)}")
        return f"[PDF Okuma Hatası: Bu dosya işlenirken bir sorun oluştu.]"