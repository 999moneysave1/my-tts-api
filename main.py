from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import edge_tts

app = FastAPI()

# किसी भी मोबाइल या वेबसाइट से कनेक्ट होने की अनुमति (CORS Bypass)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "TTS API Running Successfully"}

@app.get("/speak")
async def speak(text: str, voice: str = "hi-IN-MadhurNeural"):
    # Microsoft Edge Neural सर्वर से सीधे कनेक्ट होकर MP3 स्ट्रीम जनरेट करता है
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
            
    # ऑडियो को बिना सर्वर पर सेव किए सीधे मोबाइल को स्ट्रीम करना
    return Response(content=audio_data, media_type="audio/mpeg")
