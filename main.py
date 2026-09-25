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
        if chunk.get("type") == "audio":
            audio_data += chunk.get("data", b"")
    return Response(content=audio_data, media_type="audio/mpeg")

@app.get("/speak-with-timestamps")
async def speak_with_timestamps(text: str, voice: str = "en-GB-SoniaNeural"):
    communicate = edge_tts.Communicate(text, voice)
    sub_maker = edge_tts.SubMaker()
    audio_data = b""
    raw_word_timings = []

    async for chunk in communicate.stream():
        c_type = str(chunk.get("type", "")).lower()

        # 1. Audio data
        if c_type == "audio":
            audio_data += chunk.get("data", b"")

        # 2. SubMaker ke zariye edge-tts internal boundary capture
        sub_maker.feed(chunk)

        # 3. Direct WordBoundary chunk capture (support both casing)
        if "word" in c_type and "boundary" in c_type:
            # edge-tts ticks (1 tick = 100ns = 1e-7 seconds)
            offset = chunk.get("offset", 0)
            duration = chunk.get("duration", 0)
            text_val = chunk.get("text", "")
            
            start_sec = offset / 10_000_000
            end_sec = (offset + duration) / 10_000_000
            raw_word_timings.append({
                "word": text_val,
                "start": round(start_sec, 3),
                "end": round(end_sec, 3)
            })

    # Agar direct chunk se empty mila ho, toh sub_maker ke cues se nikaalein
    if not raw_word_timings and hasattr(sub_maker, "cues") and sub_maker.cues:
        for cue in sub_maker.cues:
            raw_word_timings.append({
                "word": cue.text,
                "start": round(cue.start.total_seconds(), 3),
                "end": round(cue.end.total_seconds(), 3)
            })

    audio_base64 = base64.b64encode(audio_data).decode("utf-8")

    return {
        "success": True,
        "voice": voice,
        "audio_base64": f"data:audio/mp3;base64,{audio_base64}",
        "words": raw_word_timings
    }
