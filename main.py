from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import edge_tts
import base64

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/speak")
async def speak(text: str, voice: str = "hi-IN-MadhurNeural"):
    # Communicate ऑब्जेक्ट बनाएँ
    communicate = edge_tts.Communicate(text, voice)
    
    audio_bytes = b""
    words_data = []

    # स्ट्रीम से ऑडियो और वर्ड बाउंड्री निकालें
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            # 100ns को सेकंड में बदलें
            words_data.append({
                "text": chunk["text"],
                "start": chunk["offset"] / 10_000_000,
                "duration": chunk["duration"] / 10_000_000
            })

    # अगर कोई शब्द नहीं मिला, तो एक खाली लिस्ट न भेजें (सुरक्षा के लिए)
    if not words_data:
        print("Warning: No word boundaries received from Edge TTS")

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    return {
        "audio": f"data:audio/mp3;base64,{audio_b64}",
        "words": words_data
    }
