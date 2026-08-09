import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

app = FastAPI(title="SmartData Reranker API")

MODEL_NAME = "Qwen/Qwen3-Reranker-0.6B"
print(f"[{MODEL_NAME}] Donanım taraması yapılıyor...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, use_fast=False)

# 🚀 1. TOKAT: Tokenizer'a zorla pad_token ekliyoruz (Hem ID hem Token olarak)
if tokenizer.pad_token_id is None:
    tokenizer.pad_token = tokenizer.eos_token or "<|endoftext|>"
    tokenizer.pad_token_id = tokenizer.eos_token_id or 151643

# Donanıma göre dinamik model yükleme
model = None
tensor_device = "cpu"

if torch.cuda.is_available():
    tensor_device = "cuda"
    print("🚀 NVIDIA (CUDA) tespit edildi. Standart PyTorch modeli GPU'ya yükleniyor...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=1, 
        trust_remote_code=True,
        torch_dtype=torch.float16 
    ).to(tensor_device)
else:
    try:
        from optimum.intel import OVModelForSequenceClassification
        print("🚀 INTEL (OpenVINO) kütüphanesi bulundu. Model GPU/XPU üzerine yükleniyor...")
        model = OVModelForSequenceClassification.from_pretrained(
            MODEL_NAME, 
            device="GPU",  
            num_labels=1, 
            trust_remote_code=True
        )
    except ImportError:
        print("⚠️ Hızlandırıcı bulunamadı. İşlemci (CPU) modunda çalışıyor.")
        tensor_device = "cpu"
        model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_NAME,
            num_labels=1, 
            trust_remote_code=True
        ).to(tensor_device)

# 🚀 2. ASIL TOKAT (SON VURUŞ): Modelin Config dosyasına pad_token_id'yi mühürlüyoruz!
if model.config.pad_token_id is None:
    model.config.pad_token_id = tokenizer.pad_token_id

if hasattr(model, "eval"):
    model.eval()

class RerankRequest(BaseModel):
    query: str
    texts: list[str]

@app.post("/api/rerank")
def rerank(req: RerankRequest):
    try:
        if not req.texts:
             return {"indices": [], "scores": []}
             
        queries = [req.query] * len(req.texts)
        
        inputs = tokenizer(
            queries, 
            req.texts, 
            padding=True, 
            truncation=True, 
            max_length=1024, 
            return_tensors="pt"
        )
        
        # Zehirli token_type_ids temizliği
        if "token_type_ids" in inputs:
            del inputs["token_type_ids"]
            
        inputs = inputs.to(tensor_device)
        
        with torch.no_grad():
            scores = model(**inputs).logits.view(-1).float().cpu().tolist()
        
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        
        return {
            "indices": ranked_indices, 
            "scores": scores
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"🚨 RERANKER PATLADI: {str(e)}") 
        raise HTTPException(status_code=500, detail=str(e))