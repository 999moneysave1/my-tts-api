from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import edge_tts
import base64

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "TTS API Running"}

@app.get("/speak")
async def speak(text: str, voice: str = "hi-IN-MadhurNeural"):
    communicate = edge_tts.Communicate(text, voice)
    audio_bytes = b""
    words_data = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            # Microsoft का समय 100-नैनोसेकंड यूनिट्स में होता है, इसे सेकंड में बदलें
            words_data.append({
                "text": chunk["text"],
                "start": chunk["offset"] / 10_000_000,
                "duration": chunk["duration"] / 10_000_000
            })

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    return JSONResponse({
        "audio": f"data:audio/mp3;base64,{audio_b64}",
        "words": words_data
    })
