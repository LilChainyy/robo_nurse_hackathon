"""
ai/stt.py

Speech-to-text via ElevenLabs Scribe (primary).
Fallback: smallest.ai Pulse → on-device Whisper.

ElevenLabs Scribe returns the transcript plus the detected language code,
which we log so the system can confirm the patient is speaking the expected language.
"""

import requests

from config import ELEVENLABS_API_KEY, ELEVENLABS_STT_MODEL, SMALLEST_API_KEY

_ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
_SMALLEST_STT_URL   = "https://waves-api.smallest.ai/api/v1/pulse/get_text"


def transcribe(audio_bytes: bytes, language: str = "es") -> str:
    """
    Transcribes audio using ElevenLabs Scribe.

    Args:
        audio_bytes: Raw WAV bytes.
        language:    Expected ISO 639-1 language code (e.g. "es", "en").
                     Passed as a hint; Scribe auto-detects regardless.

    Returns:
        Transcribed text string, or empty string on failure.
    """
    try:
        response = requests.post(
            _ELEVENLABS_STT_URL,
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={
                "model_id":      ELEVENLABS_STT_MODEL,
                "language_code": language,
            },
            timeout=20,
        )
        response.raise_for_status()
        data            = response.json()
        text            = data.get("text", "").strip()
        detected_lang   = data.get("language_code", "?")
        print(f"[STT] ElevenLabs ({detected_lang}): {text}")
        return text

    except requests.RequestException as e:
        print(f"[STT] ElevenLabs error: {e}. Trying smallest.ai fallback...")
        return _transcribe_smallest(audio_bytes, language)


def _transcribe_smallest(audio_bytes: bytes, language: str) -> str:
    """smallest.ai Pulse fallback."""
    try:
        response = requests.post(
            _SMALLEST_STT_URL,
            headers={"Authorization": f"Bearer {SMALLEST_API_KEY}"},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"language": language},
            timeout=20,
        )
        response.raise_for_status()
        text = response.json().get("text", "").strip()
        print(f"[STT/smallest] ({language}): {text}")
        return text

    except requests.RequestException as e:
        print(f"[STT] smallest.ai error: {e}. Trying Whisper fallback...")
        return _transcribe_whisper(audio_bytes)


def _transcribe_whisper(audio_bytes: bytes) -> str:
    """On-device Whisper fallback (pip install openai-whisper)."""
    try:
        import tempfile
        import whisper

        model = whisper.load_model("base")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        result = model.transcribe(tmp_path)
        text = result.get("text", "").strip()
        print(f"[STT/Whisper]: {text}")
        return text
    except ImportError:
        print("[STT] Whisper not installed: pip install openai-whisper")
        return ""
    except Exception as e:
        print(f"[STT] Whisper error: {e}")
        return ""
