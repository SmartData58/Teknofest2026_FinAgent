import json
import os
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from generate_response import get_chatbot_response

app = FastAPI(title="SmartData Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat_endpoint(
    prompt: str = Form(""),
    model: str = Form("qwen2.5:7b"),
    thinking: str = Form("false"),
    history: str = Form("[]"),  # Nuxt JSON string olarak gönderir
    file: UploadFile = File(None)
):
    try:
        parsed_history = json.loads(history)
    except Exception:
        parsed_history = []

    file_context = ""
    if file:
        file_ext = os.path.splitext(file.filename)[1].lower()
        # İleride döküman okuyucularınız buraya entegre edilecek
        file_context = f"\n\n[Kullanıcı sisteme bir dosya yükledi. Dosya adı: {file.filename}]"

    return await get_chatbot_response(
        user_message=prompt,
        model=model,
        thinking=thinking,
        history=parsed_history,
        file_context=file_context
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("chatbot:app", host="0.0.0.0", port=8000, reload=True)