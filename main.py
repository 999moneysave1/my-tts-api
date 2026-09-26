import base64
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import edge_tts

app = FastAPI(title="Edge TTS Multi-Accent & Speed Control Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_rate(rate_str: str) -> str:
    if not rate_str or not rate_str.strip():
        return "+0%"
    clean = rate_str.strip().replace(" ", "+")
    if not clean.endswith("%"):
        clean += "%"
    if clean in ["0%", "+0%", "-0%"]:
        return "+0%"
    return clean

@app.get("/")
def home():
    return {"status": "TTS Multi-Voice API Running Successfully"}

@app.get("/speak")
async def speak(text: str, voice: str = "en-GB-SoniaNeural", rate: str = "-12%"):
    safe_rate = format_rate(rate)
    communicate = edge_tts.Communicate(text, voice, rate=safe_rate)
    audio_data = b""
    async for chunk in communicate.stream():
        if isinstance(chunk, dict) and chunk.get("type") == "audio":
            audio_data += chunk.get("data", b"")
    return Response(content=audio_data, media_type="audio/mpeg")

@app.get("/speak-with-timestamps")
async def speak_with_timestamps(text: str, voice: str = "en-GB-SoniaNeural", rate: str = "-12%"):
    try:
        safe_rate = format_rate(rate)
        communicate = edge_tts.Communicate(text, voice, rate=safe_rate)
        audio_data = b""
        word_timings = []

        async for chunk in communicate.stream():
            if not isinstance(chunk, dict):
                continue
            c_type = chunk.get("type", "")

            if c_type == "audio":
                audio_data += chunk.get("data", b"")
            elif c_type == "WordBoundary":
                offset = chunk.get("offset", 0)
                duration = chunk.get("duration", 0)
                text_word = chunk.get("text", "")
                word_timings.append({
                    "word": text_word,
                    "start": round(offset / 10_000_000.0, 3),
                    "end": round((offset + duration) / 10_000_000.0, 3)
                })

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
            "rate": safe_rate,
            "audio_base64": f"data:audio/mp3;base64,{audio_base64}",
            "words": word_timings
        }
    except Exception as err:
        return {"success": False, "error": str(err), "words": []}
