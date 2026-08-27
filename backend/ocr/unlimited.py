"""Yerel OCR motoru (baidu/Unlimited-OCR).

Bu modül GÖRSELLERİ YERELDE okur; yarışma sunucusundaki LLM'e görsel
GÖNDERMEZ. Bu bilinçli bir tercih: uzak modelin istek başına 2 görsel sınırı
var, çok sayfalı PDF'ler bu sınıra hemen takılıyor.

🛠️ ÜÇ DÜZELTME (27.08.2026 — ölçümle bulundu)

1) transformers 5.x UYUMU
   Model `trust_remote_code` ile geliyor ve uzak kodu
   `transformers.utils.import_utils.is_torch_fx_available` sembolünü import
   ediyor. Bu sembol transformers 5.x'te KALDIRILDI, dolayısıyla model her
   açılışta şu hatayla düşüyordu:
       cannot import name 'is_torch_fx_available'
   Sonuç: `model=None` ve her sayfa için "[HATA: OCR Motoru sistemde aktif
   değil!]". transformers'ı geri sürüme düşürmek (diğer bileşenleri riske
   atar) yerine sembol geri kondu — karşılığı olan `torch.fx` hâlâ mevcut.

2) CİHAZ SEÇİMİ
   Kod koşulsuz `.cuda()` çağırıyordu. GPU'suz bir konteynerde bu, modelin
   yüklenmesini tamamen imkânsız kılıyordu. Artık GPU varsa bfloat16 ile
   GPU'ya, yoksa float32 ile CPU'ya yükleniyor (yavaş ama çalışıyor).

3) TEMBEL YÜKLEME
   Model import anında yükleniyordu; yani backend her açılışta ~4 GB'lık
   ağırlığı beklemek zorundaydı — OCR hiç kullanılmayacak olsa bile.
   Artık ilk gerçek OCR isteğinde yükleniyor.
"""
import asyncio
import os
import shutil
import tempfile

import torch
from loguru import logger

MODEL_ADI = os.getenv("OCR_MODEL", "baidu/Unlimited-OCR")

_model = None
_tokenizer = None
_yukleme_denendi = False
_yukleme_hatasi = ""
_kilit = asyncio.Lock()


def _uyumluluk_yamasi() -> None:
    """transformers 5.x'te kaldırılan ama uzak kodun beklediği sembolleri koyar."""
    try:
        import transformers.utils as U
        import transformers.utils.import_utils as IU
    except Exception:
        return

    if not hasattr(IU, "is_torch_fx_available"):
        def is_torch_fx_available() -> bool:
            try:
                import torch.fx  # noqa: F401
                return True
            except Exception:
                return False

        IU.is_torch_fx_available = is_torch_fx_available
        U.is_torch_fx_available = is_torch_fx_available
        logger.debug("transformers uyumluluk yaması: is_torch_fx_available geri kondu.")


def _modeli_yukle() -> None:
    """Modeli bir kez yükler. Hata olursa sebebini saklar, uygulamayı düşürmez."""
    global _model, _tokenizer, _yukleme_denendi, _yukleme_hatasi
    if _yukleme_denendi:
        return
    _yukleme_denendi = True

    _uyumluluk_yamasi()

    gpu_var = torch.cuda.is_available()
    cihaz = "cuda" if gpu_var else "cpu"
    dtype = torch.bfloat16 if (gpu_var and torch.cuda.is_bf16_supported()) else torch.float32

    logger.info(
        f"🧠 {MODEL_ADI} yükleniyor... (cihaz={cihaz}, dtype={str(dtype).split('.')[-1]}) "
        f"İlk açılışta model indirileceği için uzun sürebilir."
    )
    try:
        from transformers import AutoModel, AutoTokenizer

        _tokenizer = AutoTokenizer.from_pretrained(MODEL_ADI, trust_remote_code=True)
        model = AutoModel.from_pretrained(
            MODEL_ADI,
            trust_remote_code=True,
            use_safetensors=True,
            torch_dtype=dtype,
        ).eval()
        _model = model.cuda() if gpu_var else model
        logger.success(f"✅ OCR motoru hazır ({cihaz}).")
    except Exception as e:
        _yukleme_hatasi = f"{type(e).__name__}: {e}"
        _model, _tokenizer = None, None
        logger.error(f"❌ OCR modeli yüklenemedi — {_yukleme_hatasi}")


def ocr_hazir_mi() -> bool:
    """Model yüklenmişse True. (Tembel yükleme yüzünden ilk çağrıdan önce False.)"""
    return _model is not None and _tokenizer is not None


async def process_image_with_ocr(image_path: str) -> str:
    """Görseli yerel OCR modeline verir ve çıkan metni döndürür."""
    # Model yükleme CPU/GPU'yu uzun süre meşgul eden eşzamanlı bir iş; olay
    # döngüsünü bloklamamak için ayrı iş parçacığında ve tek seferlik kilitle.
    async with _kilit:
        if not _yukleme_denendi:
            await asyncio.to_thread(_modeli_yukle)

    if not ocr_hazir_mi():
        return f"[HATA: OCR Motoru sistemde aktif değil! ({_yukleme_hatasi or 'model yüklenmedi'})]"

    try:
        logger.info(f"👁️ Görsel OCR işlemine alındı: {image_path}")
        out_dir = tempfile.mkdtemp(prefix="ocr_out_")

        infer_kwargs = dict(
            prompt="<image>document parsing.",
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

        # Çıkarım da bloklayıcı; olay döngüsünü serbest bırak.
        await asyncio.to_thread(_model.infer, _tokenizer, **infer_kwargs)

        # infer sonuçları txt/md olarak diske yazıyor.
        result_text = ""
        for fname in sorted(os.listdir(out_dir)):
            if fname.endswith((".txt", ".md")):
                with open(os.path.join(out_dir, fname), "r", encoding="utf-8") as f:
                    result_text += f.read() + "\n"

        shutil.rmtree(out_dir, ignore_errors=True)

        if result_text.strip():
            logger.success(f"✨ OCR başarılı: {image_path}")
            return result_text.strip()
        return "[Uyarı: Model bu görselden metin çıkaramadı.]"

    except Exception as e:
        logger.error(f"OCR okuma hatası: {e}")
        return "[Görsel Okuma Hatası: Görsel anlaşılamadı veya bozuk.]"
