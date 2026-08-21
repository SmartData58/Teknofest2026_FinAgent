import torch
import os
import tempfile
import shutil
from transformers import AutoModel, AutoTokenizer
from loguru import logger

MODEL_NAME = "baidu/Unlimited-OCR"

logger.info(f"🧠 {MODEL_NAME} modeli GPU'ya yükleniyor... (Bu işlem ilk açılışta biraz sürebilir)")

try:
    # Orijinal mimariye uygun olarak AutoModel ve bfloat16 kullanıyoruz[cite: 3]
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    
    model = AutoModel.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        use_safetensors=True,          # Safetensors ağırlıklarını zorluyoruz[cite: 3]
        torch_dtype=torch.bfloat16,    # Orijinal kaynak bfloat16 istiyor[cite: 3]
    ).eval().cuda()
    
    logger.success("✅ Baidu Unlimited-OCR başarıyla GPU'ya yüklendi ve hazır!")
    
except Exception as e:
    logger.error(f"❌ OCR Modeli yüklenirken hata oluştu: {str(e)}")
    model, tokenizer = None, None


async def process_image_with_ocr(image_path: str) -> str:
    """
    Gelen görseli Baidu OCR modeline sokar ve metni geçici dosyadan okur.
    """
    if model is None or tokenizer is None:
        return "[HATA: OCR Motoru sistemde aktif değil!]"
        
    try:
        logger.info(f"👁️ Görsel OCR işlemine alındı: {image_path}")
        
        # Orijinal mimarinin gerektirdiği geçici çıktı klasörünü oluştur[cite: 3]
        out_dir = tempfile.mkdtemp(prefix="ocr_out_")
        
        prompt = "document parsing."
        
        # Modelin özel infer parametreleri[cite: 3]
        _infer_kwargs = dict(
            prompt=f"<image>{prompt}",
            image_file=image_path,
            output_path=out_dir,
            base_size=1024,
            image_size=1024,
            crop_mode=False,
            max_length=8192,
            no_repeat_ngram_size=35,
            ngram_window=128,
            save_results=True,
        )
        
        # Chat yerine doğrudan modelin özel infer metodunu çalıştırıyoruz[cite: 3]
        model.infer(tokenizer, **_infer_kwargs)
        
        # Infer metodu çıktıları txt/md olarak kaydettiği için dosyaları okuyup birleştiriyoruz[cite: 3]
        result_text = ""
        for fname in sorted(os.listdir(out_dir)):
            if fname.endswith((".txt", ".md")):
                with open(os.path.join(out_dir, fname), "r", encoding="utf-8") as f:
                    result_text += f.read() + "\n"
                    
        # İşimiz bitince geçici çıktı klasörünü sil
        shutil.rmtree(out_dir, ignore_errors=True)
        
        # Eğer klasörde okunan bir metin varsa döndür
        if result_text.strip():
            logger.success(f"✨ OCR Başarılı! Metin çıkarıldı: {image_path}")
            return result_text.strip()
        else:
            return "[Uyarı: Model bu görselden metin çıkaramadı.]"
        
    except Exception as e:
        logger.error(f"OCR okuma işlemi sırasında hata: {str(e)}")
        return f"[Görsel Okuma Hatası: Görsel anlaşılamadı veya bozuk.]"