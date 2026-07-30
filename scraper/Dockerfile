# Microsoft'un resmi Playwright Python imajı (Chromium kurulu gelir)
FROM mcr.microsoft.com/playwright/python:v1.61.0-jammy

WORKDIR /app

# --- 3. YÖNTEM BURAYA EKLENİYOR ---
# Python'a /app klasörünü ana modül dizini olarak tanıtıyoruz.
# Bu sayede 'from db.database import ...' komutu hatasız çalışır.
ENV PYTHONPATH=/app
# ---------------------------------

# Gereksinimleri yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodları kopyala
COPY . .

# Scraper'ı 8002 portundan dinlemeye alıyoruz
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]