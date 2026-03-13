"""
test_modules.py
---------------
Verify each module independently before wiring into main.py.

Usage:
    python test_modules.py stt          # mic → Pulse STT
    python test_modules.py tts          # Lightning TTS → speaker
    python test_modules.py translate    # DeepL EN↔ES
    python test_modules.py pipeline     # full doctor→patient round-trip
    python test_modules.py screening    # full nurse screening conversation
"""

import sys
from hardware.audio import record, play
from ai.stt import transcribe
from ai.tts import speak
from ai.translate import en_to_es, es_to_en, doctor_to_patient, patient_to_doctor


def test_stt():
    print("\n=== STT TEST (smallest.ai Pulse) ===")
    input("Press Enter, then speak in English for 5 seconds:")
    audio = record(seconds=5)
    text = transcribe(audio, language="en")
    print(f"Transcribed: '{text}'")


def test_tts():
    print("\n=== TTS TEST (smallest.ai Lightning V2) ===")
    print("Playing English...")
    play(speak("Hello, I am your medical assistant. How can I help you today?", language="en"))
    print("Playing Spanish...")
    play(speak("Hola, soy su asistente médico. ¿En qué puedo ayudarle hoy?", language="es"))
    print("Done.")


def test_translate():
    print("\n=== TRANSLATION TEST (DeepL) ===")
    en = "The doctor says you should take this medicine twice a day with food."
    print(f"EN: {en}")
    print(f"ES: {en_to_es(en)}")

    es = "Tengo dolor de cabeza y fiebre desde ayer por la noche."
    print(f"\nES: {es}")
    print(f"EN: {es_to_en(es)}")


def test_pipeline():
    print("\n=== DOCTOR→PATIENT PIPELINE TEST ===")
    print("Speak English for 6 seconds.")
    input("Press Enter to start:")
    en, es = doctor_to_patient(record_seconds=6)
    print(f"\nDoctor (EN): {en}")
    print(f"Patient hears (ES): {es}")


def test_screening():
    print("\n=== NURSE SCREENING TEST (GPT-4o) ===")
    from ai.nurse_screening import run_screening

    def stt_fn():
        input("  (Press Enter, then speak for 7s):")
        return transcribe(record(seconds=7), language="en")

    def tts_play_fn(text: str):
        play(speak(text, language="en"))

    summary = run_screening(stt_fn=stt_fn, tts_play_fn=tts_play_fn)
    print("\nSummary dict returned to main.py:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "pipeline"
    {
        "stt":       test_stt,
        "tts":       test_tts,
        "translate": test_translate,
        "pipeline":  test_pipeline,
        "screening": test_screening,
    }.get(mode, test_pipeline)()
