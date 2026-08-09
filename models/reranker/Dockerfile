FROM python:3.10-slim

# Dışarıdan compose üzerinden gelecek donanım sinyali (Varsayılan: intel)
ARG HARDWARE=intel

USER root
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Temel bağımlılıklar (Her iki donanımda da ortak olanlar)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# İŞTE AKILLI SEÇİCİ: Donanıma göre sadece ilgili yapay zeka motorunu kurar
RUN if [ "$HARDWARE" = "intel" ]; then \
        echo "Intel OpenVINO GPU altyapısı kuruluyor..." && \
        pip install --no-cache-dir optimum-intel[openvino] openvino ; \
    else \
        echo "NVIDIA CUDA altyapısı kuruluyor..." && \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 ; \
    fi

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]