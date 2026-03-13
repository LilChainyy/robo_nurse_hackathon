"""
main.py — MedRover Session Orchestrator

State machine:
    IDLE → DETECT → GREET → INTAKE → SUMMARIZE → RELAY → (next patient)

Current scope: Spanish-speaking patient ↔ English-speaking doctor.
Hardware stub: face detection falls back to keypress if camera is unavailable.
Navigation (rover movement) is a no-op stub until Pi/Cyberwave is wired up.
"""

import sys

from hardware.camera import detect_face
from hardware.audio  import record, play
from ai.stt   import transcribe
from ai.tts   import speak
from ai.agent import (translate, generate_clinical_summary, extract_structured_data,
                       start_nurse_conversation, next_nurse_turn, NURSE_INTRO_EN)
from db.mongo import save_patient_session, update_status, print_priority_queue

# ---------------------------------------------------------------------------
# Session language config (swap these to support other pairs)
# ---------------------------------------------------------------------------
PATIENT_LANG_CODE = "es"
PATIENT_LANG_NAME = "Spanish"
DOCTOR_LANG_CODE  = "en"
DOCTOR_LANG_NAME  = "English"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _say(text_en: str, lang_code: str, lang_name: str):
    """Translate English text → patient language, then speak it."""
    translated = translate(text_en, "English", lang_name)
    print(f"  [MedRover → {lang_name}] {translated}")
    audio = speak(translated, lang_code)
    if audio:
        play(audio)


def _say_en(text: str):
    """Speak directly in English (for doctor-facing prompts)."""
    print(f"  [MedRover → English] {text}")
    audio = speak(text, "en")
    if audio:
        play(audio)


def _divider(label: str = ""):
    width = 60
    print("\n" + "=" * width)
    if label:
        pad = (width - len(label) - 2) // 2
        print(" " * pad + f" {label} ")
        print("=" * width)


# ---------------------------------------------------------------------------
# State: DETECT
# ---------------------------------------------------------------------------

def state_detect() -> bool:
    """
    Returns True when a patient is confirmed present.
    Falls back to operator keypress if camera is unavailable.
    """
    _divider("WAITING FOR PATIENT")
    detected = detect_face(timeout=20)

    if not detected:
        print("[Detect] Camera did not find a face.")
        ans = input("  Operator: manually confirm patient present? (y/n): ").strip().lower()
        return ans == "y"

    return True


# ---------------------------------------------------------------------------
# State: GREET
# ---------------------------------------------------------------------------

def state_greet() -> str:
    """
    Greet the patient and ask for their name.
    Returns the patient's name as a string.
    """
    _divider("GREET")

    # Ask for name
    ask_name_en = "Hello! Before we begin, may I have your name please?"
    ask_name_native = _speak_to_patient(ask_name_en)

    raw_audio   = record(seconds=5)
    name_native = transcribe(raw_audio, language=PATIENT_LANG_CODE)
    name        = translate(name_native, PATIENT_LANG_NAME, "English").strip()
    print(f"  [Patient name] {name}")

    # Acknowledge
    ack_en = f"Thank you, {name}. I will now ask you a few questions before the doctor sees you."
    _speak_to_patient(ack_en)

    return name


# ---------------------------------------------------------------------------
# State: INTAKE
# ---------------------------------------------------------------------------

def _speak_to_patient(text_en: str):
    """Translate English text to patient language and speak it. Returns the translation."""
    text_native = translate(text_en, "English", PATIENT_LANG_NAME)
    print(f"  [→ {PATIENT_LANG_NAME}] {text_native}")
    audio = speak(text_native, PATIENT_LANG_CODE)
    if audio:
        play(audio)
    return text_native


def state_intake() -> tuple[list[dict], list[dict]]:
    """
    Conversational nurse intake driven by GPT-4o (always in English internally).

    Translation layer:
      - Nurse question (EN) → translated to patient language → spoken via TTS
      - Patient speaks in their language → STT → translated back to EN → fed to GPT-4o

    Returns:
        english_log  — full conversation in English (for summary + doctor view)
        native_log   — full conversation in patient's language (for audit)

    Both logs use: [{"role": "nurse"|"patient", "text": "..."}]
    """
    _divider("NURSE INTAKE")
    english_log = []
    native_log  = []

    # --- Intro (fixed, always the same) ---
    print(f"\n  [MedRover intro (EN)] {NURSE_INTRO_EN}")
    intro_native = _speak_to_patient(NURSE_INTRO_EN)
    english_log.append({"role": "nurse", "text": NURSE_INTRO_EN})
    native_log.append( {"role": "nurse", "text": intro_native})

    # --- GPT-4o opens with first question (English) ---
    print("\n  [Nurse] Generating first question...")
    history, _, first_question_en = start_nurse_conversation()
    print(f"  [Nurse (EN)] {first_question_en}")
    first_question_native = _speak_to_patient(first_question_en)
    english_log.append({"role": "nurse", "text": first_question_en})
    native_log.append( {"role": "nurse", "text": first_question_native})

    turn = 1
    while True:
        # Record patient answer in their language
        print(f"\n  [Turn {turn}] Recording patient ({PATIENT_LANG_NAME})...")
        raw_audio = record(seconds=8)
        patient_native = transcribe(raw_audio, language=PATIENT_LANG_CODE)
        print(f"  [Patient ({PATIENT_LANG_NAME})] {patient_native}")

        if not patient_native.strip():
            retry_en = "I'm sorry, I didn't catch that. Could you please repeat?"
            retry_native = _speak_to_patient(retry_en)
            native_log.append({"role": "nurse", "text": retry_native})
            english_log.append({"role": "nurse", "text": retry_en})
            continue

        # Log patient's original response in their language
        native_log.append({"role": "patient", "text": patient_native})

        # Translate to English before feeding to GPT-4o
        patient_en = translate(patient_native, PATIENT_LANG_NAME, "English")
        print(f"  [Patient (EN)] {patient_en}")
        english_log.append({"role": "patient", "text": patient_en})

        # GPT-4o generates next nurse response in English
        history, nurse_reply_en, done = next_nurse_turn(history, patient_en)
        print(f"  [Nurse (EN)] {nurse_reply_en}")
        english_log.append({"role": "nurse", "text": nurse_reply_en})

        nurse_reply_native = _speak_to_patient(nurse_reply_en)
        native_log.append({"role": "nurse", "text": nurse_reply_native})

        if done:
            print("\n  [Intake] Conversation complete.")
            break

        turn += 1

    return english_log, native_log


# ---------------------------------------------------------------------------
# State: SUMMARIZE
# ---------------------------------------------------------------------------

def state_summarize(
    name: str,
    english_log: list[dict],
    native_log: list[dict],
) -> tuple[str, str]:
    """
    Extracts structured data + generates clinical summary, saves to MongoDB,
    then prints the priority queue.

    Returns (clinical_summary, session_id).
    """
    _divider("CLINICAL SUMMARY — FOR DOCTOR")
    print("  Extracting structured data...")
    structured = extract_structured_data(english_log)

    print("  Generating clinical summary...")
    summary = generate_clinical_summary(english_log)

    print()
    print(summary)
    print()

    print(f"  Severity score : {structured.get('severity_score')}/10")
    print(f"  Risk level     : {structured.get('risk_level', '').upper()}")

    # Save to MongoDB
    session_id = save_patient_session(
        name=name,
        language_code=PATIENT_LANG_CODE,
        language_name=PATIENT_LANG_NAME,
        english_log=english_log,
        native_log=native_log,
        structured=structured,
        clinical_summary=summary,
    )

    # Show updated priority queue for doctor
    print_priority_queue()

    return summary, session_id


# ---------------------------------------------------------------------------
# State: RELAY — bidirectional live translation
# ---------------------------------------------------------------------------

def state_relay():
    """
    Live translation between doctor (English) and patient (Spanish).

    Operator controls flow via keypress:
        D — doctor speaks English → patient hears Spanish
        P — patient speaks Spanish → doctor reads English
        Q — end relay
    """
    _divider("RELAY — DOCTOR ↔ PATIENT")
    _say("The doctor will speak with you now.", PATIENT_LANG_CODE, PATIENT_LANG_NAME)

    print(
        "\n  Controls:\n"
        "    D  — Doctor speaks (English → Spanish for patient)\n"
        "    P  — Patient speaks (Spanish → English for doctor)\n"
        "    Q  — End relay and move to next patient\n"
    )

    while True:
        mode = input("  Mode [D/P/Q]: ").strip().upper()

        if mode == "Q":
            _say("Thank you. The doctor will see you shortly.", PATIENT_LANG_CODE, PATIENT_LANG_NAME)
            print("[Relay] Session ended.")
            break

        elif mode == "D":
            print(f"  [Recording doctor ({DOCTOR_LANG_NAME})...]")
            audio = record(seconds=8)
            text_en = transcribe(audio, language=DOCTOR_LANG_CODE)
            print(f"  [Doctor (English)] {text_en}")

            if text_en:
                text_patient = translate(text_en, "English", PATIENT_LANG_NAME)
                print(f"  [→ {PATIENT_LANG_NAME}] {text_patient}")
                patient_audio = speak(text_patient, PATIENT_LANG_CODE)
                if patient_audio:
                    play(patient_audio)

        elif mode == "P":
            print(f"  [Recording patient ({PATIENT_LANG_NAME})...]")
            audio = record(seconds=8)
            text_native = transcribe(audio, language=PATIENT_LANG_CODE)
            print(f"  [Patient ({PATIENT_LANG_NAME})] {text_native}")

            if text_native:
                text_en = translate(text_native, PATIENT_LANG_NAME, "English")
                print(f"  [→ English for doctor] {text_en}")
                # Speak English translation aloud so doctor can hear it too
                doctor_audio = speak(text_en, DOCTOR_LANG_CODE)
                if doctor_audio:
                    play(doctor_audio)

        else:
            print("  Invalid input. Use D, P, or Q.")


# ---------------------------------------------------------------------------
# Navigation stub (no-op until Pi/Cyberwave is connected)
# ---------------------------------------------------------------------------

def move_to_next_patient():
    """
    Stub: move rover ~1m forward to next patient.
    Replace with hardware.navigation.move_forward(duration=2.0) on the Pi.
    """
    print("[Navigation] (stub) Rover moving to next patient...")
    # from hardware.navigation import move_forward
    # move_forward(duration=2.0)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("  MedRover — Starting")
    print(f"  Patient language : {PATIENT_LANG_NAME} ({PATIENT_LANG_CODE})")
    print(f"  Doctor language  : {DOCTOR_LANG_NAME} ({DOCTOR_LANG_CODE})")
    print("=" * 60)

    patient_num = 1

    while True:
        print(f"\n{'='*60}")
        print(f"  PATIENT {patient_num}")
        print(f"{'='*60}")

        # --- DETECT ---
        patient_present = state_detect()
        if not patient_present:
            print("[Session] No patient confirmed. Exiting.")
            break

        # --- GREET (collects patient name) ---
        name = state_greet()

        # --- INTAKE ---
        english_log, native_log = state_intake()

        # --- SUMMARIZE + SAVE TO DB ---
        summary, session_id = state_summarize(name, english_log, native_log)

        # --- RELAY ---
        input("\n  Operator: press Enter when doctor is ready for relay... ")
        update_status(session_id, "with_doctor")
        state_relay()
        update_status(session_id, "done")

        # --- NEXT PATIENT ---
        print()
        ans = input(f"  Move to patient {patient_num + 1}? (y/n): ").strip().lower()
        if ans == "y":
            move_to_next_patient()
            patient_num += 1
        else:
            print("\n[MedRover] Session complete. Goodbye.")
            sys.exit(0)


if __name__ == "__main__":
    main()
