"""
ai/tts.py

Text-to-speech via ElevenLabs (primary).
Fallback: gTTS if ElevenLabs is unavailable.

ElevenLabs returns raw PCM (24 kHz, 16-bit mono) which we wrap into a WAV
so the rest of the codebase gets consistent bytes from speak().
"""

import io
import struct
import wave

import requests

from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

_TTS_URL  = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_MODEL    = "eleven_multilingual_v2"   # supports ES, EN, FR, HI, AR, DE, PT, etc.
_PCM_RATE = 24000


def speak(text: str, language: str = "en") -> bytes:
    """
    Converts text to speech using ElevenLabs multilingual v2.

    Args:
        text:     Text to synthesise.
        language: ISO 639-1 code, e.g. "en", "es".

    Returns:
        WAV audio bytes, or empty bytes on failure.
    """
    if not text.strip():
        return b""

    url = _TTS_URL.format(voice_id=ELEVENLABS_VOICE_ID)

    try:
        response = requests.post(
            url,
            headers={
                "xi-api-key":   ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text":          text,
                "model_id":      _MODEL,
                "output_format": "pcm_24000",   # raw 16-bit PCM, 24 kHz, mono
                "voice_settings": {
                    "stability":        0.5,
                    "similarity_boost": 0.75,
                },
            },
            timeout=20,
        )
        response.raise_for_status()
        pcm_bytes = response.content
        wav_bytes = _pcm_to_wav(pcm_bytes, sample_rate=_PCM_RATE)
        print(f"[TTS] ElevenLabs ({language}): {text[:60]}...")
        return wav_bytes

    except requests.RequestException as e:
        print(f"[TTS] ElevenLabs error: {e}. Falling back to gTTS...")
        return _speak_gtts(text, language)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000,
                channels: int = 1, sample_width: int = 2) -> bytes:
    """Wraps raw 16-bit PCM bytes in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def _speak_gtts(text: str, language: str) -> bytes:
    """gTTS fallback (pip install gtts pydub)."""
    try:
        from gtts import gTTS
        from pydub import AudioSegment

        tts = gTTS(text=text, lang=language)
        mp3_buf = io.BytesIO()
        tts.write_to_fp(mp3_buf)
        mp3_buf.seek(0)
        audio = AudioSegment.from_mp3(mp3_buf)
        wav_buf = io.BytesIO()
        audio.export(wav_buf, format="wav")
        print(f"[TTS/gTTS] ({language}): {text[:60]}...")
        return wav_buf.getvalue()

    except ImportError:
        print("[TTS] gTTS/pydub not installed: pip install gtts pydub")
        return b""
    except Exception as e:
        print(f"[TTS] gTTS error: {e}")
        return b""
