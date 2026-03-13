"""
tests/test_ai_pipeline.py — Person B

Run from medrover/ directory:
    python tests/test_ai_pipeline.py

Validates independently (no hardware needed — uses a pre-recorded WAV):
  1. Claude translation  English → Spanish
  2. Claude translation  Spanish → English
  3. TTS — synthesize a Spanish sentence
  4. STT — transcribe a pre-recorded Spanish wav (or a generated one)
  5. Full mini round-trip: speak English → TTS → STT → translate back
  6. Clinical summary generation

Requires: SMALLEST_API_KEY and CLAUDE_API_KEY in .env
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_translation_en_to_es():
    print("\n[Test 1] Translation — English → Spanish")
    from ai.agent import translate
    result = translate("What are your main symptoms today?", "English", "Spanish")
    ok = len(result) > 5 and result != "What are your main symptoms today?"
    print(f"  Input : What are your main symptoms today?")
    print(f"  Output: {result}")
    print(f"  → {'PASS' if ok else 'FAIL'}")
    return result if ok else None


def test_translation_es_to_en():
    print("\n[Test 2] Translation — Spanish → English")
    from ai.agent import translate
    spanish = "Tengo dolor de cabeza y fiebre desde ayer."
    result = translate(spanish, "Spanish", "English")
    ok = len(result) > 5
    print(f"  Input : {spanish}")
    print(f"  Output: {result}")
    print(f"  → {'PASS' if ok else 'FAIL'}")
    return ok


def test_tts_spanish(text: str = None):
    print("\n[Test 3] TTS — synthesizing Spanish speech")
    from ai.tts import speak
    phrase = text or "¿Cuáles son sus síntomas principales hoy?"
    audio = speak(phrase, language="es")
    ok = len(audio) > 1000
    print(f"  Text  : {phrase}")
    print(f"  Bytes : {len(audio)}")
    print(f"  → {'PASS' if ok else 'FAIL — empty audio returned'}")
    return audio if ok else None


def test_tts_english():
    print("\n[Test 4] TTS — synthesizing English speech")
    from ai.tts import speak
    phrase = "The doctor will see you now."
    audio = speak(phrase, language="en")
    ok = len(audio) > 1000
    print(f"  Text  : {phrase}")
    print(f"  Bytes : {len(audio)}")
    print(f"  → {'PASS' if ok else 'FAIL — empty audio returned'}")
    return audio if ok else None


def test_stt_with_generated_audio(spanish_audio: bytes = None):
    print("\n[Test 5] STT — transcribing Spanish audio")
    if not spanish_audio:
        print("  → SKIP — no audio from TTS test to feed into STT")
        return None

    from ai.stt import transcribe
    # Write audio to temp file, then transcribe
    import tempfile, wave, io

    # smallest.ai expects a WAV file uploaded; just pass the bytes directly
    result = transcribe(spanish_audio, language="es")
    ok = len(result) > 2
    print(f"  Transcript: {result}")
    print(f"  → {'PASS' if ok else 'FAIL — empty transcript'}")
    return result if ok else None


def test_stt_roundtrip(spanish_phrase: str = None):
    print("\n[Test 6] Round-trip — TTS(es) → STT(es) → translate → English")
    from ai.tts import speak
    from ai.stt import transcribe
    from ai.agent import translate

    phrase = spanish_phrase or "Me duele la cabeza y tengo fiebre."
    print(f"  Original Spanish : {phrase}")

    audio = speak(phrase, language="es")
    if not audio:
        print("  → FAIL at TTS step")
        return False

    transcript = transcribe(audio, language="es")
    print(f"  Transcribed      : {transcript}")

    if not transcript:
        print("  → FAIL at STT step")
        return False

    back_to_english = translate(transcript, "Spanish", "English")
    print(f"  Translated back  : {back_to_english}")
    print(f"  → PASS — full round-trip complete")
    return True


def test_nurse_conversation():
    print("\n[Test 7] Nurse conversation — GPT-4o drives the intake")
    from ai.agent import start_nurse_conversation, next_nurse_turn

    history, intro, first_question = start_nurse_conversation()
    print(f"  [Intro]         {intro}")
    print(f"  [First question] {first_question}")
    ok = len(intro) > 10 and len(first_question) > 10
    print(f"  → {'PASS — intro and first question are separate' if ok else 'FAIL'}")

    # Simulate one patient turn
    history, reply, done = next_nurse_turn(history, "Me duele mucho la cabeza y tengo fiebre.")
    print(f"  [Patient] Me duele mucho la cabeza y tengo fiebre.")
    print(f"  [Nurse reply] {reply}")
    print(f"  [Done?] {done}")
    print(f"  → {'PASS' if reply else 'FAIL — empty nurse reply'}")
    return history


def test_clinical_summary(history: list = None):
    print("\n[Test 8] Clinical summary from conversation history")
    from ai.agent import generate_clinical_summary, start_nurse_conversation, next_nurse_turn

    if not history:
        # Build a minimal synthetic English log
        history = [
            {"role": "nurse",   "text": "Hello, I am MedRover. I will ask you a few questions."},
            {"role": "nurse",   "text": "What brings you in today?"},
            {"role": "patient", "text": "I have a headache and fever since yesterday."},
            {"role": "nurse",   "text": "How long have you had these symptoms?"},
            {"role": "patient", "text": "About two days."},
            {"role": "nurse",   "text": "On a scale of 1 to 10, how severe is your pain?"},
            {"role": "patient", "text": "Around 6 out of 10."},
            {"role": "nurse",   "text": "Do you have any known medication allergies?"},
            {"role": "patient", "text": "I am allergic to penicillin."},
            {"role": "nurse",   "text": "Are you currently taking any medications?"},
            {"role": "patient", "text": "I am taking ibuprofen for the pain."},
        ]

    summary = generate_clinical_summary(history)
    ok = "CHIEF COMPLAINT" in summary
    print(f"\n{summary}\n")
    print(f"  → {'PASS' if ok else 'FAIL — unexpected format'}")
    return ok


if __name__ == "__main__":
    print("=" * 50)
    print("  MedRover — AI Pipeline Tests (Person B)")
    print("=" * 50)

    translated = test_translation_en_to_es()
    test_translation_es_to_en()
    spanish_audio = test_tts_spanish(translated)
    test_tts_english()
    transcript = test_stt_with_generated_audio(spanish_audio)
    test_stt_roundtrip()
    history = test_nurse_conversation()
    test_clinical_summary(history)

    print("\n" + "=" * 50)
    print("  Done. Fix any FAILs before integration.")
    print("=" * 50)
