"""
ai/translate.py

English ↔ Spanish translation via DeepL.
(smallest.ai Pulse = STT only, Lightning = TTS only — no translation.)

Also exposes two high-level convenience functions:
  - doctor_to_patient(): record EN → transcribe → translate → speak ES
  - patient_to_doctor(): record ES → transcribe → translate → speak EN

These build on the existing stt.py, tts.py, and hardware/audio.py modules.
"""

import deepl

from config import DEEPL_API_KEY
from ai.stt import transcribe
from ai.tts import speak
from hardware.audio import record, play

_translator = deepl.Translator(DEEPL_API_KEY)


# ---------------------------------------------------------------------------
# Core translation
# ---------------------------------------------------------------------------

def en_to_es(text: str) -> str:
    """Translate English text → Spanish."""
    if not text.strip():
        return ""
    result = _translator.translate_text(text, source_lang="EN", target_lang="ES")
    translated = result.text
    print(f"[Translate EN→ES]: {translated}")
    return translated


def es_to_en(text: str) -> str:
    """Translate Spanish text → English."""
    if not text.strip():
        return ""
    result = _translator.translate_text(text, source_lang="ES", target_lang="EN-US")
    translated = result.text
    print(f"[Translate ES→EN]: {translated}")
    return translated


# ---------------------------------------------------------------------------
# High-level pipeline helpers
# ---------------------------------------------------------------------------

def doctor_to_patient(record_seconds: int = 8) -> tuple[str, str]:
    """
    Doctor speaks English → patient hears Spanish.

    Records from mic, transcribes, translates, and plays Spanish audio.

    Returns:
        (english_text, spanish_text)
    """
    audio = record(seconds=record_seconds)
    english_text = transcribe(audio, language="en")

    if not english_text:
        play(speak("Sorry, I didn't catch that. Please try again.", language="en"))
        return "", ""

    print(f"  [Doctor  → EN]: {english_text}")
    spanish_text = en_to_es(english_text)
    play(speak(spanish_text, language="es"))
    return english_text, spanish_text


def patient_to_doctor(record_seconds: int = 8) -> tuple[str, str]:
    """
    Patient speaks Spanish → doctor hears English.

    Records from mic, transcribes, translates, and plays English audio.

    Returns:
        (spanish_text, english_text)
    """
    audio = record(seconds=record_seconds)
    spanish_text = transcribe(audio, language="es")

    if not spanish_text:
        play(speak("No entendí. Por favor repita.", language="es"))
        return "", ""

    print(f"  [Patient → ES]: {spanish_text}")
    english_text = es_to_en(spanish_text)
    play(speak(english_text, language="en"))
    return spanish_text, english_text
