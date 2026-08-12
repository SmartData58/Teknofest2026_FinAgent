from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import subprocess
import logging

# Loglama ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str

def run_spiders():
    """Arka planda runner.py'yi çalıştırarak verileri MongoDB'ye akıtır."""
    try:
        logger.info("Örümcekler (Spiders) serbest bırakılıyor, veriler MongoDB'ye akıyor...")
        # az önce güncellediğimiz runner.py dosyasını çalıştırır
        subprocess.run(["python", "runner.py", "--hepsi"], check=True)
        logger.info("Kazıma işlemi tamamlandı ve veriler MongoDB'ye yazıldı!")
    except Exception as e:
        logger.error(f"Kazıma işlemi sırasında hata oluştu: {e}")

@app.post("/scrape")
def perform_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    logger.info(f"Backend'den kazıma emri geldi! (İstek URL: {request.url})")
    
    # İşlemi arka plana atıyoruz ki sistem donmasın, API anında yanıt versin
    background_tasks.add_task(run_spiders)
    
    return {
        "status": "success", 
        "message": "Kazıyıcı başarıyla tetiklendi, örümcekler verileri toplayıp MongoDB'ye aktarıyor."
    }