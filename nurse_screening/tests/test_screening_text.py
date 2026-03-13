"""
tests/test_screening_text.py

Text-only screening test — no mic, no audio, no API keys except OpenAI.
Type patient responses directly in the terminal.

Run from medrover/ directory:
    python tests/test_screening_text.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.agent import (
    NURSE_INTRO_EN,
    extract_structured_data,
    generate_clinical_summary,
    next_nurse_turn,
    start_nurse_conversation,
    translate,
)

PATIENT_LANG_NAME = "Spanish"


def _show(role: str, text_en: str, text_es: str):
    tag = "🤖 MedRover" if role == "nurse" else "🧑 Patient"
    print(f"\n  {tag}")
    print(f"  ┌─ EN : {text_en}")
    print(f"  └─ ES : {text_es}")


def run():
    print("\n" + "=" * 62)
    print("  MEDROVER — Text Screening Test (no audio)")
    print("  Type patient responses in Spanish when prompted.")
    print("=" * 62)

    name = input("\n  Patient name: ").strip() or "Test Patient"
    english_log, native_log = [], []

    # Intro
    intro_es = translate(NURSE_INTRO_EN, "English", PATIENT_LANG_NAME)
    _show("nurse", NURSE_INTRO_EN, intro_es)
    english_log.append({"role": "nurse", "text": NURSE_INTRO_EN})
    native_log.append( {"role": "nurse", "text": intro_es})

    # First question
    gpt_history, _, first_q_en = start_nurse_conversation()
    first_q_es = translate(first_q_en, "English", PATIENT_LANG_NAME)
    _show("nurse", first_q_en, first_q_es)
    english_log.append({"role": "nurse", "text": first_q_en})
    native_log.append( {"role": "nurse", "text": first_q_es})

    # Conversation loop
    turn = 1
    while True:
        patient_es = input(f"\n  [Turn {turn}] Your response (Spanish): ").strip()
        if not patient_es:
            continue

        patient_en = translate(patient_es, PATIENT_LANG_NAME, "English")
        _show("patient", patient_en, patient_es)
        english_log.append({"role": "patient", "text": patient_en})
        native_log.append( {"role": "patient", "text": patient_es})

        gpt_history, nurse_reply_en, done = next_nurse_turn(gpt_history, patient_en)
        nurse_reply_es = translate(nurse_reply_en, "English", PATIENT_LANG_NAME)
        _show("nurse", nurse_reply_en, nurse_reply_es)
        english_log.append({"role": "nurse", "text": nurse_reply_en})
        native_log.append( {"role": "nurse", "text": nurse_reply_es})

        if done:
            break
        turn += 1

    # Summary
    print("\n" + "=" * 62)
    print("  CLINICAL SUMMARY")
    print("=" * 62)
    structured = extract_structured_data(english_log)
    summary    = generate_clinical_summary(english_log)
    print(f"\n{summary}")
    print(f"\n  Severity : {structured.get('severity_score')}/10  |  Risk : {structured.get('risk_level','').upper()}")
    print(f"  Symptoms : {', '.join(structured.get('symptoms', []))}")

    save = input("\n  Save to MongoDB? (y/n): ").strip().lower()
    if save == "y":
        from db.mongo import save_patient_session, print_priority_queue
        sid = save_patient_session(
            name=name,
            language_code="es", language_name=PATIENT_LANG_NAME,
            english_log=english_log, native_log=native_log,
            structured=structured, clinical_summary=summary,
        )
        print(f"  Saved → session_id: {sid}")
        print_priority_queue()


if __name__ == "__main__":
    run()
