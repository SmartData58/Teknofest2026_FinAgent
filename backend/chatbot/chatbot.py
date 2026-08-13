from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI(title="SmartData Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#OLLAMA_URL = "http://llm-1:11434/api/generate"
OLLAMA_URL = "http://localhost:11434/api/generate"

@app.post("/api/chat")
async def chat_endpoint(
    # FormData ile gelen alanları Form ve File ile yakalıyoruz
    prompt: str = Form(""),
    model: str = Form("qwen2.5:7b"),
    # model: str = Form("qwen"),
    file: UploadFile = File(None)
):
    file_context = ""
    
    if file:
        file_ext = os.path.splitext(file.filename)[1].lower()
        print(f"Alınan dosya: {file.filename}, Uzantı: {file_ext}")
        
        # İleride 'document_processor' dizinindeki (pdf.py, image.py, excel.py vb.) 
        # modüller bu aşamada çağırılacak ve dosyanın içeriği metne dökülecek.
        
        file_context = f"\n\n[Kullanıcı sisteme bir dosya yükledi. Dosya adı: {file.filename}. Dosya türü desteklenmektedir.]"
        
    final_prompt = prompt + file_context

    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "model": model,
                "prompt": final_prompt,
                "stream": False
            }
            # Ollama'ya isteği ilet
            response = await client.post(OLLAMA_URL, json=payload, timeout=60.0)
            response.raise_for_status()
            
            data = response.json()
            return {"response": data.get("response", "")}
            
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Ollama bağlantı hatası: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)