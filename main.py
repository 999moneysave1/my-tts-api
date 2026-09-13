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
    submaker = edge_tts.SubMaker()
    
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
            
    # ऑडियो को Base64 में और हर शब्द का सटीक टाइमस्टैम्प JSON में भेजना
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    return JSONResponse({
        "audio": f"data:audio/mp3;base64,{audio_b64}",
        "cues": submaker.cues
    })
