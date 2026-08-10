import pandas as pd
from loguru import logger

async def extract_text_from_excel(file_path: str) -> str:
    try:
        logger.info(f"📊 Excel okunuyor: {file_path}")
        # sheet_name=None tüm sekmeleri bir sözlük (dictionary) olarak okur
        dfs = pd.read_excel(file_path, sheet_name=None)
        
        text_parts = []
        for sheet_name, df in dfs.items():
            text_parts.append(f"\n[Sekme Adı: {sheet_name}]")
            # NaN (boş) hücreleri boşlukla değiştir ve tabloyu metne çevir
            text_parts.append(df.fillna("").to_string(index=False))
            
        logger.success(f"✅ Excel başarıyla okundu: {file_path}")
        return "\n".join(text_parts)
    
    except Exception as e:
        logger.error(f"Excel okuma hatası ({file_path}): {str(e)}")
        return "[Hata: Bu Excel dosyası okunamadı veya bozuk.]"