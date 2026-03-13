# MedRover API Guide

**Base URL:** `http://<server-ip>:8000`
**Interactive docs (try it live):** `http://<server-ip>:8000/docs`

Start the server:
```bash
cd medrover
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

---

## For the Pi / Hardware Person — Nurse Screening Flow

The Pi handles audio I/O. The API handles all AI logic.
Flow: start session → loop answers until `done=true` → done.

---

### 1. Start a session

```
POST /session/start
Content-Type: multipart/form-data

Fields:
  patient_name   string   Patient's name
  language_code  string   "es"      (default)
  language_name  string   "Spanish" (default)
```

**Response:**
```json
{
  "session_id": "abc-123",
  "intro_text": "Hola, soy MedRover...",
  "intro_audio_b64": "<base64 WAV>",
  "first_question_text_native": "¿Cuál es el motivo de su visita hoy?",
  "first_question_audio_b64": "<base64 WAV>"
}
```

- Decode `intro_audio_b64` → play it
- Decode `first_question_audio_b64` → play it
- Save `session_id` for all subsequent calls

---

### 2. Submit patient answer → get next nurse response

Call this after every patient answer. Repeat until `done = true`.

```
POST /session/{session_id}/answer
Content-Type: multipart/form-data

Fields (send one):
  audio   file     WAV recording of patient speaking
  text    string   Patient's typed response (for testing without mic)
```

**Response:**
```json
{
  "patient_transcript_native": "Tengo dolor de cabeza",
  "patient_text_en": "I have a headache",
  "nurse_reply_text_native": "¿Desde cuándo tiene ese dolor?",
  "nurse_reply_audio_b64": "<base64 WAV>",
  "done": false
}
```

- Decode and play `nurse_reply_audio_b64`
- When `done = true`, the response also includes:

```json
{
  "done": true,
  "session_id": "abc-123",
  "clinical_summary": "CHIEF COMPLAINT: ...",
  "severity_score": 7,
  "risk_level": "high"
}
```

Session is automatically saved to MongoDB when `done = true`.

---

### 3. Relay — live doctor ↔ patient translation (after intake)

**Doctor speaks English → patient hears Spanish:**
```
POST /relay/{session_id}/doctor
Fields:
  audio   file     WAV of doctor speaking  (or)
  text    string   Doctor's typed message
```

**Patient speaks Spanish → doctor reads English:**
```
POST /relay/{session_id}/patient
Fields:
  audio   file     WAV of patient speaking  (or)
  text    string   Patient's typed message
```

Both return:
```json
{
  "original_text": "...",
  "translated_text": "...",
  "translated_audio_b64": "<base64 WAV>"
}
```

---

### 4. Update patient status

```
PATCH /session/{session_id}/status
Content-Type: application/json

{ "status": "with_doctor" }   ← when doctor starts seeing patient
{ "status": "done" }          ← when visit is complete
```

---

### Decoding audio (Python example)

```python
import base64, io, sounddevice as sd, soundfile as sf

def play_b64_audio(b64_string):
    wav_bytes = base64.b64decode(b64_string)
    data, rate = sf.read(io.BytesIO(wav_bytes))
    sd.play(data, rate)
    sd.wait()
```

---

## For the Frontend Person — Doctor Dashboard

### Get the priority queue

Returns all waiting patients sorted by severity (highest first).

```
GET /queue
```

**Response:**
```json
[
  {
    "session_id": "abc-123",
    "name": "Maria Lopez",
    "chief_complaint": "Chest pain and shortness of breath",
    "symptoms": ["chest pain", "shortness of breath"],
    "severity_score": 9,
    "risk_level": "critical",
    "pain_level": 7,
    "checked_in_at": "2026-03-13T10:30:00+00:00"
  },
  {
    "session_id": "def-456",
    "name": "Juan Garcia",
    "chief_complaint": "Headache and fever for 2 days",
    "symptoms": ["headache", "fever"],
    "severity_score": 6,
    "risk_level": "medium",
    "pain_level": 6,
    "checked_in_at": "2026-03-13T10:45:00+00:00"
  }
]
```

Poll this endpoint every 10–15 seconds to keep the queue live.

---

### Get full patient summary

Call this when the doctor clicks on a patient to see their full intake note.

```
GET /session/{session_id}/summary
```

**Response:**
```json
{
  "session_id": "abc-123",
  "name": "Maria Lopez",
  "clinical_summary": "CHIEF COMPLAINT: Chest pain and shortness of breath\nHISTORY: Symptoms started 3 hours ago...\nPAIN LEVEL: 7/10\nALLERGIES: None known\nCURRENT MEDICATIONS: Aspirin 81mg daily\nCLINICAL NOTES: Patient reports pain radiating to left arm.",
  "chief_complaint": "Chest pain and shortness of breath",
  "symptoms": ["chest pain", "shortness of breath", "left arm pain"],
  "pain_level": 7,
  "allergies": [],
  "current_medications": ["Aspirin 81mg"],
  "severity_score": 9,
  "risk_level": "critical"
}
```

---

### Update patient status

When the doctor starts seeing a patient or marks them as done:

```
PATCH /session/{session_id}/status
Content-Type: application/json

{ "status": "with_doctor" }
{ "status": "done" }
```

This removes them from the waiting queue.

---

## Quick Reference

| Who | Endpoint | What it does |
|---|---|---|
| Pi | `POST /session/start` | Begin intake, get intro + first question |
| Pi | `POST /session/{id}/answer` | Send patient answer, get next question |
| Pi | `POST /relay/{id}/doctor` | Doctor audio → Spanish for patient |
| Pi | `POST /relay/{id}/patient` | Patient audio → English for doctor |
| Pi | `PATCH /session/{id}/status` | Mark as with_doctor / done |
| Frontend | `GET /queue` | All waiting patients, priority sorted |
| Frontend | `GET /session/{id}/summary` | Full intake note for one patient |
