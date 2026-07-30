from fastapi import FastAPI
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import psycopg2

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str

def save_to_db(baslik, kaynak):
    # Veritabanına bağla ve veriyi yaz
    conn = psycopg2.connect(host="postgres", database="smartdata", user="user", password="password")
    cur = conn.cursor()
    cur.execute("INSERT INTO kampanyalar (baslik, kaynak) VALUES (%s, %s)", (baslik, kaynak))
    conn.commit()
    cur.close()
    conn.close()

@app.post("/scrape")
def perform_scrape(request: ScrapeRequest):
    try:
        with sync_playwright() as p:
            # Bot gizleme argümanları
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            try:
                # domcontentloaded ile maksimum 15 saniye bekle
                page.goto(request.url, wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                # Timeout olsa bile sayfada bir şeyler yüklenmiş olabilir, ÇÖKME, DEVAM ET!
                print(f"Goto uyarısı (Önemli değil): {str(e)}")
            
            # JS bloklamalarını geçmek veya sayfanın oturmasını beklemek için sabit 3 saniye bekle
            page.wait_for_timeout(3000)
            
            title = page.title()
            
            # Eğer başlık bomboş gelirse, en azından bir bilgi yazalım
            if not title:
                title = "Başlık alınamadı (Güvenlik Duvarı Engeli)"
            
            # Her ne olursa olsun veritabanına KAYDET!
            save_to_db(title, request.url)
            
            browser.close()
            return {"status": "success", "baslik": title}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}