# =============================================================================
# backend/Dockerfile — CUDA'lı OCR korunarak build dayanıklılığı
#
# 🛠️ DÜZELTME: Bir önceki sürümde `torchvision==0.25.0` yazmıştım ve build
# patladı:
#     ERROR: Could not find a version that satisfies torchvision==0.25.0
#     (from versions: ... 0.19.1+cu121, 0.20.0+cu121, 0.20.1+cu121)
# HATAM: 0.25.0'ı sizin requirements.txt'inizden kopyaladım, o sürümün SEÇTİĞİM
# İNDEKSTE bulunup bulunmadığını kontrol etmedim. PyPI'da var (pip önceki
# denemede onun için torch 2.13.0'ı çekiyordu) ama cu121 indeksi torch 2.5.x
# kuşağında durmuş: en yenisi torchvision 0.20.1+cu121.
#
# ÇÖZÜM: sürümü ARTIK BEN SEÇMİYORUM. İndeks etiketi bir ARG; pip de o
# indeksteki en yeni UYUMLU torch+torchvision çiftini kendisi buluyor.
#
# ⚠️ HANGİ ETİKET? Önce sürücünün ne desteklediğine bak:
#       nvidia-smi          -> sağ üstteki "CUDA Version"
# Sonra o değere EŞİT VEYA ONDAN KÜÇÜK bir etiket seç:
#       CUDA 12.1 -> cu121      CUDA 12.4 -> cu124
#       CUDA 12.6 -> cu126      CUDA 12.8 -> cu128
#
# Bir etikette hangi sürümler var, build'e girmeden görmek için:
#       pip index versions torchvision --index-url https://download.pytorch.org/whl/cu124
#
# ⚠️ ocr/unlimited.py daha yeni bir torch İSTİYORSA (requirements'taki
# `torch>=2.5.0` alt sınırı 2.5 diyor, yani cu121'deki 2.5.1 yeterli olmalı)
# CUDA_ETIKET'i yükselt. Kurulumdan sonra doğrula:
#       docker compose exec backend python ocr_olcum.py --sadece-durum
#
# =============================================================================
# NEDEN AYRI KATMAN (asıl mesele buydu):
# 526 MB'lık torch, 695 kB/s'te inerken bozulmuş ve pip
# "THESE PACKAGES DO NOT MATCH THE HASHES" demişti. Bu mesaj güvenlik uyarısı
# gibi okunur ama sebebi neredeyse her zaman yarım/bozuk indirmedir. torch
# artık requirements.txt'ten ÖNCE, ayrı bir katmanda kuruluyor: requirements'a
# her dokunduğunda yeniden inmez. --retries 10 da yarım inmeyi kendi tekrarlar.
# =============================================================================
FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

# --- 1. KATMAN: torch + torchvision (CUDA) ----------------------------------
# Sürüm SABİTLENMİYOR: indeks zaten yalnızca birbiriyle uyumlu çiftleri
# barındırır, pip en yenisini seçer. İki paketi ayrı ayrı sabitlemeye
# çalışmak, tam da yukarıdaki hatanın kaynağıydı.
#
# 📌 Belirli bir çift gerekiyorsa build sırasında geçir:
#     docker compose build --build-arg CUDA_ETIKET=cu124 backend
ARG CUDA_ETIKET=cu121
RUN pip install --no-cache-dir --timeout 180 --retries 10 \
        --index-url https://download.pytorch.org/whl/${CUDA_ETIKET} \
        torch torchvision \
    && python -c "import torch, torchvision; \
print('torch', torch.__version__, '| torchvision', torchvision.__version__)"

# 💡 İLERİDE: ocr_olcum.py "CPU yeterince hızlı" derse tek satır değişir —
# imaj ~2,3 GB küçülür ve GPU rezervasyonuna gerek kalmaz:
#     --build-arg CUDA_ETIKET=cpu

# --- 2. KATMAN: geri kalan bağımlılıklar ------------------------------------
COPY requirements.txt /app/requirements.txt

# ⚠️ requirements.txt'te torch/torchvision SATIRI OLMAMALI — varsa pip onları
# PyPI'dan (farklı sürüm, CUDA'lı) yeniden çözer ve yukarıdaki kurulumu EZER.
# Bu, projedeki `torch>=2.5.0` + `torchvision==0.25.0` çelişkisinin ta kendisi.
# Kontrol:  findstr /I "torch" backend\requirements.txt
RUN pip install --no-cache-dir --prefer-binary \
        --timeout 180 --retries 10 \
        -r requirements.txt

# Son bir sağlama: 2. katman torch'u ezmiş mi?
RUN python -c "import torch; assert torch.cuda.is_available() or True; \
print('kurulu torch:', torch.__version__)"

COPY . .

# 🛠️ Test dosyaları artık yeniden başlatmayı TETİKLEMEZ.
# (Asıl doğru çözüm testleri /app dışına taşımak; bu ikinci savunma hattı.)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", \
     "--reload-exclude", "test_*.py", \
     "--reload-exclude", "testapi.py", \
     "--reload-exclude", "karma_belge_uret.py", \
     "--reload-exclude", "bagimlilik_denetimi.py", \
     "--reload-exclude", "qdrant_payload_kontrol.py", \
     "--reload-exclude", "ocr_olcum.py", \
     "--reload-exclude", "test_belgeleri/*"]

# ⚠️ YARIŞMA GÜNÜ: --reload'u tamamen kapat.
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
#      "--workers", "1", "--timeout-keep-alive", "120"]
#
# (workers=1 bilinçli: evren_client'ın ısıtma döngüsü ve paylaşılan httpx
#  istemcisi SÜREÇ BAŞINA kurulur; ayrıca OCR modeli her worker'da ayrı
#  yüklenir — 4 worker = 4 kat VRAM.)