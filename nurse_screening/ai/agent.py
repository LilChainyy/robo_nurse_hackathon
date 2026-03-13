"""
ai/agent.py

All language intelligence via GPT-4o (OpenAI):
  - Conversational nurse intake (dynamic follow-up questions)
  - Translation (any language pair)
  - Clinical summary generation
  - Medicine name extraction from OCR text
"""

from openai import OpenAI
from config import OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY)
_MODEL  = "gpt-4o"

# Sentinel the nurse emits when it has gathered enough information
_INTAKE_DONE_SIGNAL = "[INTAKE_COMPLETE]"

# Fixed intro in English — translated to the patient's language before speaking.
# Stored in English in the conversation log for the doctor.
NURSE_INTRO_EN = (
    "Hello, I am MedRover, your medical assistant. "
    "Before the doctor sees you, I will ask you a few brief questions about how you are feeling today. "
    "Your answers will help the doctor better understand your situation. "
    "Please speak clearly and take your time."
)

_NURSE_SYSTEM_PROMPT = """You are MedRover, a compassionate and professional medical assistant conducting a brief patient intake interview before the doctor arrives.

Conduct the ENTIRE conversation in English. The patient's responses will be translated into English for you before you receive them, so always respond in English.

The patient has already been introduced to you. Start directly with your first question — do NOT introduce yourself again.

Your goals — gather the following, in any order that feels natural:
- Chief complaint (what brings them in today)
- How long they have had the symptoms
- Severity of pain or discomfort (ask them to rate 1–10)
- Any known medication allergies
- Any medications or supplements they are currently taking
- Their zipcode or postal code (needed so the doctor can look up nearby pharmacy prices)

Guidelines:
- Ask ONE question at a time.
- Listen to the answer and follow up naturally — if something needs clarification, ask about it.
- Be warm, patient, and reassuring.
- Keep the interview brief: 3–5 questions maximum. The entire screening must fit within 1–3 minutes.
- Ask only what is essential. Do not probe further than necessary — one follow-up per topic at most.
- Do NOT ask the same thing twice.
- Always refer to yourself as MedRover if you need to use a name.
- When you have enough information to write a clinical note, end your final message with exactly: [INTAKE_COMPLETE]
  (put it on its own line at the end)

Example closing:
  "Thank you so much for your time. The doctor will be with you shortly.
  [INTAKE_COMPLETE]"
"""


# ---------------------------------------------------------------------------
# Conversational nurse intake
# ---------------------------------------------------------------------------

def start_nurse_conversation() -> tuple[list[dict], str, str]:
    """
    Starts the nurse intake.

    Returns:
        history        — conversation history to pass into next_nurse_turn()
        intro          — fixed MedRover self-introduction (speak this first)
        first_question — GPT-4o's opening clinical question (speak this after intro)
    """
    history = [{"role": "system", "content": _NURSE_SYSTEM_PROMPT}]

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=history,
        temperature=0.4,
    )
    first_question = response.choices[0].message.content.strip()
    first_question = first_question.replace(_INTAKE_DONE_SIGNAL, "").strip()
    history.append({"role": "assistant", "content": first_question})

    return history, NURSE_INTRO_EN, first_question


def next_nurse_turn(history: list[dict], patient_answer: str) -> tuple[list[dict], str, bool]:
    """
    Submits the patient's answer and gets the nurse's next response.

    Args:
        history:        Running conversation history (mutated in place).
        patient_answer: Transcribed patient speech in Spanish.

    Returns:
        (updated_history, nurse_text_to_speak, intake_complete)
        nurse_text_to_speak has the [INTAKE_COMPLETE] signal stripped out.
    """
    history.append({"role": "user", "content": patient_answer})

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=history,
        temperature=0.4,
    )
    nurse_reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": nurse_reply})

    done = _INTAKE_DONE_SIGNAL in nurse_reply
    speakable = nurse_reply.replace(_INTAKE_DONE_SIGNAL, "").strip()

    return history, speakable, done


# ---------------------------------------------------------------------------
# Clinical summary
# ---------------------------------------------------------------------------

def generate_clinical_summary(english_log: list[dict]) -> str:
    """
    Generates a structured clinical intake note in English for the doctor.

    Args:
        english_log: List of {"role": "nurse"|"patient", "text": "..."}
                     — all entries already in English.
    """
    transcript = "\n".join(
        f"{'MedRover' if e['role'] == 'nurse' else 'Patient'}: {e['text']}"
        for e in english_log
    )

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a medical assistant. Generate a concise clinical intake note "
                    "in English for the attending physician based on the nurse–patient "
                    "transcript below. Use exactly this format:\n\n"
                    "CHIEF COMPLAINT: ...\n"
                    "HISTORY: ...\n"
                    "PAIN LEVEL: .../10\n"
                    "ALLERGIES: ...\n"
                    "CURRENT MEDICATIONS: ...\n"
                    "CLINICAL NOTES: ..."
                ),
            },
            {
                "role": "user",
                "content": f"Transcript:\n\n{transcript}",
            },
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Structured data extraction  (for MongoDB storage + priority queue)
# ---------------------------------------------------------------------------

def extract_structured_data(english_log: list[dict]) -> dict:
    """
    Extracts structured clinical fields from the English conversation log.
    Used to populate the MongoDB document and drive patient prioritization.

    Returns a dict with:
        chief_complaint     str
        symptoms            list[str]
        pain_level          int   (1–10, patient-reported)
        allergies           list[str]
        current_medications list[str]
        severity_score      int   (1–10, clinical risk assessed by GPT-4o —
                                   may differ from pain_level, e.g. chest pain
                                   at 4/10 could score 9 due to cardiac risk)
        risk_level          str   ("low" | "medium" | "high" | "critical")
    """
    import json

    transcript = "\n".join(
        f"{'MedRover' if e['role'] == 'nurse' else 'Patient'}: {e['text']}"
        for e in english_log
    )

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a clinical triage assistant. Extract structured data from "
                    "the nurse–patient intake transcript and return ONLY valid JSON — "
                    "no markdown, no explanation.\n\n"
                    "Schema:\n"
                    "{\n"
                    '  "chief_complaint": "string",\n'
                    '  "symptoms": ["string"],\n'
                    '  "pain_level": 0,\n'
                    '  "allergies": ["string"],\n'
                    '  "current_medications": ["string"],\n'
                    '  "zipcode": "string",\n'
                    '  "severity_score": 0,\n'
                    '  "risk_level": "low|medium|high|critical"\n'
                    "}\n\n"
                    "severity_score (1–10): your independent clinical risk assessment — "
                    "consider symptom type, duration, combinations, and red flags, "
                    "not just the patient's stated pain level.\n"
                    "risk_level: low=1-3, medium=4-6, high=7-8, critical=9-10."
                ),
            },
            {
                "role": "user",
                "content": f"Transcript:\n\n{transcript}",
            },
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return {
            "chief_complaint": "",
            "symptoms": [],
            "pain_level": 0,
            "allergies": [],
            "current_medications": [],
            "zipcode": "",
            "severity_score": 0,
            "risk_level": "unknown",
        }


# ---------------------------------------------------------------------------
# Translation  (used for doctor ↔ patient relay)
# ---------------------------------------------------------------------------

def translate(text: str, from_lang: str, to_lang: str) -> str:
    """
    Translates `text` from `from_lang` to `to_lang`.
    Returns original text unchanged if languages are the same.
    """
    if from_lang.lower() == to_lang.lower():
        return text

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Translate the following from {from_lang} to {to_lang}. "
                    f"Return ONLY the translation — no explanation, no quotes:\n\n{text}"
                ),
            }
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Medicine extraction  (for prescription OCR)
# ---------------------------------------------------------------------------

def extract_medicine_names(ocr_text: str) -> list[str]:
    """Extracts medicine/drug names from raw OCR text of a prescription."""
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract only the medicine or drug names from this prescription text. "
                    "Return as a comma-separated list, nothing else:\n\n"
                    f"{ocr_text}"
                ),
            }
        ],
        temperature=0.0,
    )
    raw = response.choices[0].message.content.strip()
    return [m.strip() for m in raw.split(",") if m.strip()]
