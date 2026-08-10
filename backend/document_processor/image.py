from loguru import logger
from ocr.unlimited import process_image_with_ocr

async def extract_text_from_image(file_path: str) -> str:
    logger.info(f"🖼️ Görsel yapay zekaya iletiliyor: {file_path}")
    
    text = await process_image_with_ocr(file_path)
    
    return f"[Görselden OCR ile Çıkarılan Metin:]\n{text}"