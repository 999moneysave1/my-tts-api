import base64
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import edge_tts

app = FastAPI(title="Edge TTS with Word Boundary Synchronization")

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
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if isinstance(chunk, dict) and chunk.get("type") == "audio":
            audio_data += chunk.get("data", b"")
    return Response(content=audio_data, media_type="audio/mpeg")

@app.get("/speak-with-timestamps")
async def speak_with_timestamps(text: str, voice: str = "en-GB-SoniaNeural"):
    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_data = b""
        word_timings = []

        async for chunk in communicate.stream():
            if not isinstance(chunk, dict):
                continue
            
            c_type = chunk.get("type", "")

            # 1. Audio Bytes Collect Karein
            if c_type == "audio":
                audio_data += chunk.get("data", b"")

            # 2. Microsoft Word Boundary Event
            elif c_type == "WordBoundary":
                offset = chunk.get("offset", 0)
                duration = chunk.get("duration", 0)
                text_word = chunk.get("text", "")

                start_sec = offset / 10_000_000.0
                end_sec = (offset + duration) / 10_000_000.0

                word_timings.append({
                    "word": text_word,
                    "start": round(start_sec, 3),
                    "end": round(end_sec, 3)
                })

        # Agar kisi wajah se word boundary empty reh jaye, safe math estimate se auto-fill karein
        # taaki backend kabhi 0 ya khali na bheje
        total_audio_sec = max(1.5, len(audio_data) / 6000.0)
        clean_words = text.strip().split()
        
        if not word_timings and clean_words:
            per_word_sec = total_audio_sec / len(clean_words)
            curr = 0.0
            for w in clean_words:
                word_timings.append({
                    "word": w,
                    "start": round(curr, 3),
                    "end": round(curr + per_word_sec, 3)
                })
                curr += per_word_sec

        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        return {
            "success": True,
            "voice": voice,
            "audio_base64": f"data:audio/mp3;base64,{audio_base64}",
            "words": word_timings
        }

    except Exception as err:
        return {
            "success": False,
            "error": str(err),
            "words": []
        }
