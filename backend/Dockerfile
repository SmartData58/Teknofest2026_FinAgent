FROM python:3.10-slim
WORKDIR /app
# Dosyaları açıkça kopyalıyoruz
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]