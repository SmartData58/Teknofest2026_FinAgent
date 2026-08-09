import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

app = FastAPI(title="SmartData Embedding API")

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
print(f"[{MODEL_NAME}] Donanım taraması yapılıyor...")

# Tokenizer yüklemesi (use_fast=False belirtilmiş)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, use_fast=False)

model = None
tensor_device = "cpu"

if torch.cuda.is_available():
    tensor_device = "cuda"
    print("🚀 NVIDIA (CUDA) tespit edildi. Standart PyTorch modeli GPU'ya yükleniyor...")
    # NVIDIA için saf Hugging Face PyTorch modeli yüklenir
    model = AutoModel.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        torch_dtype=torch.float16 # VRAM tasarrufu
    ).to(tensor_device)
else:
    # CUDA yoksa Intel (XPU/OpenVINO) veya Saf CPU denenir
    try:
        from optimum.intel import OVModelForFeatureExtraction
        print("🚀 INTEL (OpenVINO) kütüphanesi bulundu. Model GPU/XPU üzerine yükleniyor...")
        model = OVModelForFeatureExtraction.from_pretrained(
            MODEL_NAME, 
            device="GPU", 
            trust_remote_code=True
        )
        # OpenVINO arka planda kendi optimize cihazını kullanır, giriş tensörleri cpu'da kalabilir.
    except ImportError:
        print("⚠️ Hızlandırıcı bulunamadı. İşlemci (CPU) modunda çalışıyor.")
        tensor_device = "cpu"
        model = AutoModel.from_pretrained(
            MODEL_NAME,
            trust_remote_code=True
        ).to(tensor_device)

# Değerlendirme modu
if hasattr(model, "eval"):
    model.eval()

class EmbedRequest(BaseModel):
    model: str | None = None
    input: list[str] | str
    keep_alive: str | None = None

@app.post("/api/embed")
def embed(req: EmbedRequest):
    try:
        texts = req.input if isinstance(req.input, list) else [req.input]
        
        inputs = tokenizer(
            texts, 
            padding=True, 
            truncation=True, 
            max_length=3000, 
            return_tensors="pt"
        ).to(tensor_device)
        
        with torch.no_grad():
            outputs = model(**inputs)
            # Ortalama havuzlama (Mean Pooling)
            embeddings = outputs.last_hidden_state.mean(dim=1)
            # L2 Normalizasyonu
            embeddings = F.normalize(embeddings, p=2, dim=1)
        
        return {"embeddings": embeddings.cpu().tolist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))