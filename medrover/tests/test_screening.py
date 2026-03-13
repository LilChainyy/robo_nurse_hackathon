"""
tests/test_screening.py

End-to-end screening test — no camera, no rover needed.
Runs the full nurse intake loop with real mic + speaker.

What happens:
  1. You enter the patient name via keyboard
  2. MedRover intro plays in Spanish, text shown in both languages
  3. GPT-4o generates each question → shown in EN + ES → spoken in Spanish
  4. Press Enter when ready → speak your answer in Spanish → 8s recording window
  5. Your Spanish is transcribed (smallest.ai STT) + translated to English
  6. Both shown on screen; nurse generates next question
  7. At the end: clinical summary printed + full session saved to MongoDB

Run from medrover/ directory:
    python tests/test_screening.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.agent import (
    NURSE_INTRO_EN,
    extract_structured_data,
    generate_clinical_summary,
    next_nurse_turn,
    start_nurse_conversation,
    translate,
)
from ai.stt import transcribe
from ai.tts import speak
from hardware.audio import record, play
from db.mongo import save_patient_session, print_priority_queue

PATIENT_LANG_CODE = "es"
PATIENT_LANG_NAME = "Spanish"


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _divider(label=""):
    print("\n" + "=" * 62)
    if label:
        print(f"  {label}")
        print("=" * 62)

def _show_bilingual(role: str, text_en: str, text_native: str):
    """Prints a turn with both English and Spanish clearly labelled."""
    tag = "🤖 MedRover" if role == "nurse" else "🧑 Patient"
    print(f"\n  {tag}")
    print(f"  ┌─ EN  : {text_en}")
    print(f"  └─ ES  : {text_native}")


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _speak_spanish(text_en: str) -> str:
    """Translate → Spanish, speak it, return the Spanish text."""
    text_es = translate(text_en, "English", PATIENT_LANG_NAME)
    audio = speak(text_es, PATIENT_LANG_CODE)
    if audio:
        play(audio)
    return text_es


def _record_patient() -> tuple[str, str]:
    """
    Waits for Enter, records 8 seconds of audio, transcribes in Spanish,
    translates to English. Returns (spanish_text, english_text).
    """
    input("\n  ── Press Enter and speak your answer in Spanish (8 seconds) ──")
    print("  🎙  Recording...")
    audio_bytes = record(seconds=8)
    print("  ✓  Done recording. Transcribing...")

    patient_es = transcribe(audio_bytes, language=PATIENT_LANG_CODE)
    if not patient_es.strip():
        print("  ⚠  No speech detected.")
        return "", ""

    patient_en = translate(patient_es, PATIENT_LANG_NAME, "English")
    return patient_es, patient_en


# ---------------------------------------------------------------------------
# Main screening flow
# ---------------------------------------------------------------------------

def run_screening():
    _divider("MEDROVER — SCREENING TEST")

    # Collect patient name
    name = input("\n  Enter patient name (for demo): ").strip() or "Test Patient"
    print(f"\n  Patient : {name}")
    print(f"  Language: {PATIENT_LANG_NAME} ({PATIENT_LANG_CODE})\n")

    english_log = []
    native_log  = []

    # ── INTRO ──────────────────────────────────────────────────────────────
    _divider("INTRO")
    intro_es = _speak_spanish(NURSE_INTRO_EN)
    _show_bilingual("nurse", NURSE_INTRO_EN, intro_es)
    english_log.append({"role": "nurse", "text": NURSE_INTRO_EN})
    native_log.append( {"role": "nurse", "text": intro_es})

    # ── FIRST QUESTION (GPT-4o) ────────────────────────────────────────────
    _divider("NURSE INTAKE")
    print("  Generating first question...")
    gpt_history, _, first_q_en = start_nurse_conversation()
    first_q_es = _speak_spanish(first_q_en)
    _show_bilingual("nurse", first_q_en, first_q_es)
    english_log.append({"role": "nurse", "text": first_q_en})
    native_log.append( {"role": "nurse", "text": first_q_es})

    # ── CONVERSATION LOOP ──────────────────────────────────────────────────
    turn = 1
    while True:
        print(f"\n  ─── Turn {turn} ───")

        patient_es, patient_en = _record_patient()

        if not patient_es:
            retry_es = _speak_spanish("I'm sorry, I didn't catch that. Could you please repeat?")
            english_log.append({"role": "nurse", "text": "I'm sorry, I didn't catch that. Could you please repeat?"})
            native_log.append( {"role": "nurse", "text": retry_es})
            continue

        _show_bilingual("patient", patient_en, patient_es)
        english_log.append({"role": "patient", "text": patient_en})
        native_log.append( {"role": "patient", "text": patient_es})

        # GPT-4o nurse reply (English)
        gpt_history, nurse_reply_en, done = next_nurse_turn(gpt_history, patient_en)
        nurse_reply_es = _speak_spanish(nurse_reply_en)
        _show_bilingual("nurse", nurse_reply_en, nurse_reply_es)
        english_log.append({"role": "nurse", "text": nurse_reply_en})
        native_log.append( {"role": "nurse", "text": nurse_reply_es})

        if done:
            print("\n  ✓  Intake complete.")
            break

        turn += 1

    # ── SUMMARY ───────────────────────────────────────────────────────────
    _divider("CLINICAL SUMMARY — FOR DOCTOR")
    print("  Extracting structured data + generating summary...")

    structured = extract_structured_data(english_log)
    summary    = generate_clinical_summary(english_log)

    print(f"\n{summary}\n")
    print(f"  Severity score : {structured.get('severity_score')}/10")
    print(f"  Risk level     : {structured.get('risk_level', '').upper()}")

    # ── SAVE TO MONGODB ────────────────────────────────────────────────────
    _divider("SAVING TO MONGODB")
    session_id = save_patient_session(
        name=name,
        language_code=PATIENT_LANG_CODE,
        language_name=PATIENT_LANG_NAME,
        english_log=english_log,
        native_log=native_log,
        structured=structured,
        clinical_summary=summary,
    )
    print(f"  ✓  Saved. session_id = {session_id}")

    print_priority_queue()

    _divider("DONE")
    return session_id


if __name__ == "__main__":
    run_screening()
