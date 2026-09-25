import base64
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import edge_tts

app = FastAPI(title="Edge TTS Multi-Accent & Speed Control Engine")

# CORS Bypass (किसी भी डोमेन या लोकलहोस्ट से बिना रोकटोक कनेक्ट करने के लिए)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_rate(rate_str: str) -> str:
    """
    यूआरएल से आने वाले रेट पैरामीटर को साफ़ और मान्य फॉर्मेट में बदलता है।
    उदाहरण: '+0%' या '0%' या खाली स्ट्रिंग को सही '0%' या '-15%' बनाता है।
    """
    if not rate_str or not rate_str.strip():
        return "+0%"
    
    clean = rate_str.strip()
    
    # यदि ब्राउज़र ने '+' को स्पेस बना दिया हो
    clean = clean.replace(" ", "+")
    
    # यदि अंत में % न लगा हो तो जोड़ें
    if not clean.endswith("%"):
        clean += "%"
        
    # यदि 0% हो तो सीधे '+0%' या '0%' रखें
    if clean in ["0%", "+0%", "-0%"]:
        return "+0%"
        
    return clean

@app.get("/")
def home():
    return {"status": "TTS Multi-Voice API Running Successfully"}

# 1. साधारण MP3 ऑडियो स्ट्रीम एंडपॉइंट
@app.get("/speak")
async def speak(text: str, voice: str = "en-GB-SoniaNeural", rate: str = "-12%"):
    safe_rate = format_rate(rate)
    communicate = edge_tts.Communicate(text, voice, rate=safe_rate)
    audio_data = b""
    async for chunk in communicate.stream():
        if isinstance(chunk, dict) and chunk.get("type") == "audio":
            audio_data += chunk.get("data", b"")
    return Response(content=audio_data, media_type="audio/mpeg")

# 2. ⚡ टाइमस्टैम्प + ऑडियो सिंक एंडपॉइंट (सभी एक्सेंट और स्पीड सपोर्ट के साथ)
@app.get("/speak-with-timestamps")
async def speak_with_timestamps(text: str, voice: str = "en-GB-SoniaNeural", rate: str = "-12%"):
    try:
        # स्पीड को माइक्रोसॉफ्ट के मान्य फॉर्मेट में सेट करना
        safe_rate = format_rate(rate)
        communicate = edge_tts.Communicate(text, voice, rate=safe_rate)
        
        audio_data = b""
        word_timings = []

        async for chunk in communicate.stream():
            if not isinstance(chunk, dict):
                continue
            
            c_type = chunk.get("type", "")

            # (A) ऑडियो बाइट्स इकट्ठा करना
            if c_type == "audio":
                audio_data += chunk.get("data", b"")

            # (B) माइक्रोसॉफ्ट का असली वर्ड बाउंड्री टाइमस्टैम्प
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

        # (C) सेफ़्टी फ़ॉलबैक: यदि बाउंड्री खाली रह जाए तो गणितीय अनुपात से भरें
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

        # ऑडियो को बेस64 स्ट्रिंग में बदलना
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        return {
            "success": True,
            "voice": voice,
            "rate": safe_rate,
            "audio_base64": f"data:audio/mp3;base64,{audio_base64}",
            "words": word_timings
        }

    except Exception as err:
        return {
            "success": False,
            "error": str(err),
            "words": []
        }
