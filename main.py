import base64
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import edge_tts

app = FastAPI(title="Edge TTS with Word Boundary Synchronization")

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
    return {"status": "TTS API with Word Timestamps Running Successfully"}

# 1. पुराना एंडपॉइंट (सीधा MP3 ऑडियो स्ट्रीम करने के लिए)
@app.get("/speak")
async def speak(text: str, voice: str = "hi-IN-MadhurNeural"):
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
            
    return Response(content=audio_data, media_type="audio/mpeg")

# 2. ⚡ नया सुपर-एक्यूरेट एंडपॉइंट (ऑडियो + वर्ड टाइमस्टैम्प दोनों के लिए)
@app.get("/speak-with-timestamps")
async def speak_with_timestamps(text: str, voice: str = "en-GB-SoniaNeural"):
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    word_timings = []

    async for chunk in communicate.stream():
        # (A) ऑडियो बाइट्स इकट्ठा करना
        if chunk["type"] == "audio":
            audio_data += chunk["data"]

        # (B) Microsoft Edge का असली Word Boundary टाइमस्टैम्प पकड़ना
        elif chunk["type"] == "WordBoundary":
            # Microsoft टाइम 100-नैनोसेकंड (ticks) में भेजता है, इसे सेकंड में बदलें
            start_sec = chunk["offset"] / 10_000_000
            duration_sec = chunk["duration"] / 10_000_000
            end_sec = start_sec + duration_sec

            word_timings.append({
                "word": chunk["text"],
                "start": round(start_sec, 3),
                "end": round(end_sec, 3)
            })

    # MP3 ऑडियो को बेस64 स्ट्रिंग में बदलना ताकि एक ही JSON में भेजा जा सके
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")

    return {
        "success": True,
        "voice": voice,
        "audio_base64": f"data:audio/mp3;base64,{audio_base64}",
        "words": word_timings
    }
