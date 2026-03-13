"""
ai/nurse_screening.py

Conducts a nurse-style intake interview with the patient in English.

Flow:
  - GPT-4o greets patient and asks questions one at a time
  - Patient responds verbally → transcribed to English text via STT
  - LLM follows up dynamically based on each response
  - After ~6-10 exchanges, LLM produces a structured clinical summary
  - Summary dict is returned to main.py for the doctor to review

Usage:
    from ai.nurse_screening import run_screening
    from hardware.audio import record, play
    from ai.stt import transcribe
    from ai.tts import speak

    summary = run_screening(
        stt_fn=lambda: transcribe(record(seconds=7), language="en"),
        tts_play_fn=lambda text: play(speak(text, language="en")),
    )
"""

from openai import OpenAI
from config import OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY)

NURSE_SYSTEM_PROMPT = """You are a warm, professional medical intake nurse assistant named Maya.
Your job is to conduct a brief initial screening with a patient before they see the doctor.

RULES:
- Ask ONE question at a time. Never ask two questions in one turn.
- Keep each question short and plain — patients may be anxious or elderly.
- Be conversational and empathetic, not clinical or robotic.
- Follow up naturally based on what the patient says:
    - If they mention pain → ask where and how severe (1-10)
    - If they mention fever → ask how high and since when
    - If they mention a fall or injury → ask what happened
- You must cover ALL of these before ending:
    1. Chief complaint (why they are here today)
    2. Duration of symptoms
    3. Severity (1-10 scale)
    4. Key associated symptoms (fever, nausea, shortness of breath, etc.)
    5. Current medications (if any)
    6. Known allergies (if any)
- After you have collected enough information (typically 6-10 exchanges), end the screening.
- To end: say a brief warm closing line, then on a NEW LINE write exactly: SCREENING_COMPLETE
  followed by the structured summary in this format (no extra text after):

SCREENING_COMPLETE
CHIEF_COMPLAINT: <one sentence>
DURATION: <e.g. "3 days", "since this morning">
SEVERITY: <number>/10
SYMPTOMS: <comma-separated list>
MEDICATIONS: <comma-separated list, or "None reported">
ALLERGIES: <comma-separated list, or "None reported">
NOTES: <anything else clinically relevant from the conversation>

Start by warmly greeting the patient and asking why they came in today."""


def _call_llm(conversation_history: list) -> str:
    """Single GPT-4o call. Returns nurse's next message."""
    messages = [{"role": "system", "content": NURSE_SYSTEM_PROMPT}] + conversation_history
    response = _client.chat.completions.create(
        model="gpt-4o",
        max_tokens=300,
        messages=messages,
    )
    return response.choices[0].message.content.strip()


def _parse_summary(raw: str) -> dict:
    """
    Parses the structured block after SCREENING_COMPLETE into a dict.
    Falls back gracefully if any field is missing.
    """
    fields = ["CHIEF_COMPLAINT", "DURATION", "SEVERITY", "SYMPTOMS",
              "MEDICATIONS", "ALLERGIES", "NOTES"]
    summary = {}
    for field in fields:
        for line in raw.splitlines():
            if line.strip().startswith(f"{field}:"):
                summary[field] = line.split(":", 1)[1].strip()
                break
        if field not in summary:
            summary[field] = "Not recorded"
    return summary


def run_screening(stt_fn, tts_play_fn) -> dict:
    """
    Runs the full nurse screening conversation.

    Args:
        stt_fn:       callable() -> str
                      Records audio from mic and returns transcribed English text.

        tts_play_fn:  callable(text: str) -> None
                      Converts English text to speech and plays it.

    Returns:
        dict with keys: CHIEF_COMPLAINT, DURATION, SEVERITY,
                        SYMPTOMS, MEDICATIONS, ALLERGIES, NOTES
    """
    conversation_history = []

    # Turn 0: nurse opens the conversation
    opening = _call_llm([{"role": "user", "content": "Begin the patient screening now."}])
    print(f"\n[Nurse]: {opening}\n")
    tts_play_fn(opening)
    conversation_history.append({"role": "assistant", "content": opening})

    # Conversation loop
    while True:
        patient_text = stt_fn()

        if not patient_text or not patient_text.strip():
            retry_msg = "I'm sorry, I didn't catch that. Could you please repeat?"
            print(f"[Nurse]: {retry_msg}\n")
            tts_play_fn(retry_msg)
            continue

        print(f"[Patient]: {patient_text}\n")
        conversation_history.append({"role": "user", "content": patient_text})

        nurse_reply = _call_llm(conversation_history)
        print(f"[Nurse]: {nurse_reply}\n")

        if "SCREENING_COMPLETE" in nurse_reply:
            parts = nurse_reply.split("SCREENING_COMPLETE", 1)

            closing_line = parts[0].strip()
            if closing_line:
                tts_play_fn(closing_line)

            summary_block = parts[1].strip() if len(parts) > 1 else ""
            summary = _parse_summary(summary_block)

            print("\n" + "=" * 50)
            print("PATIENT INTAKE SUMMARY")
            print("=" * 50)
            for k, v in summary.items():
                print(f"  {k}: {v}")
            print("=" * 50 + "\n")

            return summary

        tts_play_fn(nurse_reply)
        conversation_history.append({"role": "assistant", "content": nurse_reply})
