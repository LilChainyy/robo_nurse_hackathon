# MedRover — End-to-End Project Plan
### Physical AI Hackathon | 4-Hour Build

---

## 1. The Problem

English-speaking doctors operating in field clinics, refugee camps, or underserved regions abroad face a critical communication barrier with non-English-speaking patients. Existing solutions — phone interpreters (LanguageLine), consumer translation apps (Google Translate), or handheld devices (Pocketalk) — share the same core failures:

- Patient must hold a device; not hands-free
- No structured clinical intake — just raw translation
- No clinical summary generated for the doctor
- No medicine availability check at point of prescription
- Not mobile; does not come to the patient

**MedRover closes all five gaps.**

---

## 2. What We're Building

A UGV Beast Rover (Raspberry Pi 4B) that:

1. Moves through a simple room setting, stopping at each patient
2. Detects the patient is present via camera (face detection)
3. Conducts a structured nurse-style intake interview in the patient's language
4. Generates a clinical summary in English for the doctor
5. Acts as a live bidirectional translator during the doctor–patient consultation
6. Captures the prescription via camera, extracts medicine names, and looks up local availability and price in real time

**Target environment for demo:** Patients seated in a row. Rover stops at each, completes the full flow, then moves forward to the next.

---

## 3. Tech Stack

| Function | Tool | Notes |
|---|---|---|
| Robot platform | UGV Beast Rover | Raspberry Pi 4B upper controller, ESP32 lower controller |
| Edge runtime | Cyberwave Edge (Docker) | Runs on Pi; bridges cloud SDK to hardware |
| Speech-to-Text | smallest.ai Pulse | `POST waves-api.smallest.ai/api/v1/pulse/get_text` |
| Text-to-Speech | smallest.ai Lightning V2 | `POST waves-api.smallest.ai/api/v1/lightning/get_speech` |
| Translation + Agent Logic | Claude Haiku (Anthropic) | Fastest Claude model; handles translate + nurse + summarize + OCR extraction |
| Face Detection | OpenCV Haar Cascade | Fully on-device, no internet needed |
| Prescription OCR | EasyOCR | On-device, no internet needed |
| Medicine Lookup | ScrapeGraph SmartScraper | `POST api.scrapegraphai.com/v1/smartscraper` |

**Supported languages (smallest.ai Lightning V2):** English, Spanish, French, Italian, German, Arabic, Hindi, Portuguese, Russian, Dutch, Polish — 16 confirmed, 30+ for ASR.

**Toolhouse:** Not used. ScrapeGraph + Claude covers all agentic needs without adding complexity.

---

## 4. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        UGV Beast Rover                       │
│                                                              │
│    [Camera]     [USB Mic]    [Speaker]    [HDMI Display]     │
│       │             │            │               │           │
│  ┌────▼─────────────▼────────────▼───────────────▼────────┐  │
│  │                   Raspberry Pi 4B                      │  │
│  │                                                        │  │
│  │   ┌─────────────────────────────────────────────────┐  │  │
│  │   │         main.py — State Machine                 │  │  │
│  │   │  IDLE → DETECT → GREET → INTAKE → SUMMARIZE     │  │  │
│  │   │        → RELAY → PRESCRIBE → NEXT_PATIENT       │  │  │
│  │   └────────┬──────────────────┬──────────────────────┘  │  │
│  │            │                  │                          │  │
│  │   ┌────────▼──────┐  ┌────────▼──────────────────────┐  │  │
│  │   │ hardware/     │  │ ai/                           │  │  │
│  │   │  camera.py    │  │  stt.py    (smallest Pulse)   │  │  │
│  │   │  audio.py     │  │  tts.py    (smallest Light.)  │  │  │
│  │   │  navigation.py│  │  agent.py  (Claude Haiku)     │  │  │
│  │   └───────────────┘  │  prescription.py (OCR+Scrape) │  │  │
│  │                      └───────────────────────────────┘  │  │
│  │                                                          │  │
│  │   ┌──────────────────────────────────────────────────┐   │  │
│  │   │      Cyberwave Edge Runtime (Docker container)   │   │  │
│  │   │      Motor commands → ESP32 → tracked wheels     │   │  │
│  │   └──────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           │ WiFi
          ┌────────────────┼───────────────────┐
          ▼                ▼                   ▼
   smallest.ai        Claude API         ScrapeGraph API
  (STT + TTS)     (translate, nurse,    (medicine price
                   summary, extract)     + availability)
```

---

## 5. Session State Machine

```
IDLE
 └─► Camera detects face
      └─► GREET — play welcome, ask patient to select language
           └─► INTAKE — ask 5 nurse questions in patient's language, record answers
                └─► SUMMARIZE — translate answers to English, generate clinical summary, display for doctor
                     └─► RELAY — bidirectional live translation (doctor ↔ patient)
                          └─► PRESCRIBE — camera captures prescription, OCR, medicine lookup, speak results to patient
                               └─► NEXT_PATIENT — rover moves forward ~1m, back to IDLE
```

---

## 6. File Structure

```
medrover/
├── main.py                  # Orchestrates entire state machine
├── config.py                # All API keys
├── requirements.txt
├── hardware/
│   ├── camera.py            # OpenCV face detection + image capture
│   ├── audio.py             # Mic recording (pyaudio) + speaker playback
│   └── navigation.py        # Cyberwave rover movement
└── ai/
    ├── stt.py               # smallest.ai Pulse STT
    ├── tts.py               # smallest.ai Lightning TTS
    ├── agent.py             # Claude: translation, nurse questions, summary
    └── prescription.py      # EasyOCR + ScrapeGraph medicine lookup
```

---

## 7. Code — Module by Module

### config.py
```python
SMALLEST_API_KEY    = "your_smallest_key"
CLAUDE_API_KEY      = "your_claude_key"
SCRAPEGRAPH_API_KEY = "your_scrapegraph_key"
```

---

### hardware/camera.py
```python
import cv2

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def detect_face(timeout=15) -> bool:
    """Returns True as soon as a face is detected within timeout seconds."""
    import time
    cap = cv2.VideoCapture(0)
    start = time.time()
    while time.time() - start < timeout:
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)
        if len(faces) > 0:
            cap.release()
            return True
    cap.release()
    return False

def capture_image(path="/tmp/prescription.jpg") -> str:
    """Captures a single frame from the camera and saves it."""
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if ret:
        cv2.imwrite(path, frame)
    return path
```

---

### hardware/audio.py
```python
import pyaudio, wave, io, subprocess, tempfile

RATE, CHANNELS, CHUNK = 16000, 1, 1024
FORMAT = pyaudio.paInt16

def record(seconds=7) -> bytes:
    """Records audio from microphone, returns WAV bytes."""
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, frames_per_buffer=CHUNK)
    frames = [stream.read(CHUNK) for _ in range(int(RATE / CHUNK * seconds))]
    stream.stop_stream()
    stream.close()
    p.terminate()

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    return buf.getvalue()

def play(audio_bytes: bytes):
    """Plays WAV audio bytes through the speaker."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        f.write(audio_bytes)
        fname = f.name
    subprocess.run(['aplay', fname], check=False)
    # Fallback if aplay fails: use pygame.mixer
```

---

### hardware/navigation.py
```python
import requests

CYBERWAVE_EDGE_URL = "http://localhost:8080"  # local Cyberwave edge runtime

def move_forward(duration=2.0):
    """Move rover forward for given duration at fixed speed."""
    try:
        requests.post(f"{CYBERWAVE_EDGE_URL}/robot/move",
                      json={"linear": 0.3, "angular": 0.0, "duration": duration},
                      timeout=5)
    except Exception as e:
        print(f"[Navigation] Move failed: {e}")

def stop():
    try:
        requests.post(f"{CYBERWAVE_EDGE_URL}/robot/move",
                      json={"linear": 0.0, "angular": 0.0, "duration": 0},
                      timeout=5)
    except Exception as e:
        print(f"[Navigation] Stop failed: {e}")
```

> **Note:** Confirm the exact Cyberwave Edge HTTP endpoint paths from the Cyberwave dashboard or SDK docs once the edge runtime is running.

---

### ai/stt.py
```python
import requests
from config import SMALLEST_API_KEY

def transcribe(audio_bytes: bytes, language: str = "en") -> str:
    """
    Transcribes audio using smallest.ai Pulse STT.
    language: ISO 639-1 code (e.g. 'en', 'es', 'hi', 'fr', 'ar')
    """
    response = requests.post(
        "https://waves-api.smallest.ai/api/v1/pulse/get_text",
        headers={"Authorization": f"Bearer {SMALLEST_API_KEY}"},
        files={"file": ("audio.wav", audio_bytes, "audio/wav")},
        data={"language": language},
        timeout=15
    )
    response.raise_for_status()
    return response.json().get("text", "")
```

---

### ai/tts.py
```python
import requests
from config import SMALLEST_API_KEY

# Verify these voice IDs from the smallest.ai dashboard before demo
VOICE_MAP = {
    "en": "emily",
    "es": "jorge",
    "hi": "arjun",
    "fr": "claire",
    "ar": "omar",
    "de": "hans",
    "pt": "lucia",
}

def speak(text: str, language: str = "en") -> bytes:
    """
    Converts text to speech using smallest.ai Lightning V2.
    Returns raw WAV audio bytes.
    """
    response = requests.post(
        "https://waves-api.smallest.ai/api/v1/lightning/get_speech",
        headers={"Authorization": f"Bearer {SMALLEST_API_KEY}"},
        json={
            "text": text,
            "voice_id": VOICE_MAP.get(language, "emily"),
            "sample_rate": 24000,
            "add_wav_header": True
        },
        timeout=15
    )
    response.raise_for_status()
    return response.content
```

---

### ai/agent.py
```python
import anthropic
from config import CLAUDE_API_KEY

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

INTAKE_QUESTIONS = [
    "What are your main symptoms today?",
    "How long have you had these symptoms?",
    "On a scale of 1 to 10, how severe is your pain or discomfort?",
    "Do you have any known allergies to medications?",
    "Are you currently taking any medications or supplements?",
]

def translate(text: str, from_lang: str, to_lang: str) -> str:
    """Translates text between any two languages using Claude Haiku."""
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content":
            f"Translate the following from {from_lang} to {to_lang}. "
            f"Return ONLY the translation, no explanation, no quotes:\n\n{text}"}]
    )
    return msg.content[0].text.strip()

def generate_summary(qa_pairs: list) -> str:
    """
    Takes a list of {q, a} dicts (all in English) and returns
    a structured clinical summary for the doctor.
    """
    qa_text = "\n".join([f"Q: {p['q']}\nA: {p['a']}" for p in qa_pairs])
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content":
            f"""You are a medical assistant generating a clinical intake note.
Based on the following patient interview (already translated to English),
write a concise structured summary for the attending physician.

Format exactly as:
CHIEF COMPLAINT: ...
HISTORY: ...
PAIN LEVEL: .../10
ALLERGIES: ...
CURRENT MEDICATIONS: ...
NOTES: (anything clinically relevant from the conversation)

Patient Interview:
{qa_text}"""}]
    )
    return msg.content[0].text.strip()

def extract_medicine_names(ocr_text: str) -> list:
    """Extracts medicine/drug names from raw OCR prescription text."""
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content":
            f"Extract only the medicine or drug names from this prescription text. "
            f"Return as a comma-separated list, nothing else:\n\n{ocr_text}"}]
    )
    return [m.strip() for m in msg.content[0].text.strip().split(",") if m.strip()]
```

---

### ai/prescription.py
```python
import easyocr
from scrapegraph_py import Client
from hardware.camera import capture_image
from ai.agent import extract_medicine_names
from config import SCRAPEGRAPH_API_KEY

reader = easyocr.Reader(['en'])
sgai = Client(api_key=SCRAPEGRAPH_API_KEY)

# Cache to avoid repeat API calls for same medicine
_medicine_cache = {}

def run_prescription_flow(country: str = "Mexico") -> list:
    """
    Full prescription flow:
    1. Capture image from camera
    2. OCR to extract text
    3. Claude extracts medicine names
    4. ScrapeGraph looks up each medicine
    Returns list of {medicine, info} dicts
    """
    print("[Prescription] Capturing prescription image...")
    img_path = capture_image()

    print("[Prescription] Running OCR...")
    results = reader.readtext(img_path)
    raw_text = " ".join([r[1] for r in results])
    print(f"[Prescription] OCR text: {raw_text}")

    medicines = extract_medicine_names(raw_text)
    print(f"[Prescription] Detected medicines: {medicines}")

    output = []
    for med in medicines:
        if med in _medicine_cache:
            info = _medicine_cache[med]
        else:
            try:
                result = sgai.smartscraper(
                    website_url=f"https://www.google.com/search?q={med}+price+pharmacy+{country}",
                    user_prompt=(
                        f"Find the price and availability of {med} in {country}. "
                        f"Return a single sentence with: medicine name, approximate price in local currency, "
                        f"and whether it is commonly available."
                    )
                )
                info = str(result.get("result", f"{med}: information not found"))
            except Exception as e:
                info = f"{med}: lookup failed ({e})"
            _medicine_cache[med] = info

        print(f"[Prescription] {med}: {info}")
        output.append({"medicine": med, "info": info})

    return output
```

---

### main.py
```python
from hardware.camera import detect_face
from hardware.audio import record, play
from hardware.navigation import move_forward, stop
from ai.stt import transcribe
from ai.tts import speak
from ai.agent import translate, generate_summary, INTAKE_QUESTIONS
from ai.prescription import run_prescription_flow

# Language selection menu
LANGUAGES = {
    "1": ("Spanish",    "es"),
    "2": ("Hindi",      "hi"),
    "3": ("French",     "fr"),
    "4": ("Arabic",     "ar"),
    "5": ("Portuguese", "pt"),
    "6": ("English",    "en"),
}

def select_language() -> tuple:
    menu = (
        "Hello! To continue in your language, press: "
        "1 for Spanish, 2 for Hindi, 3 for French, "
        "4 for Arabic, 5 for Portuguese, 6 for English."
    )
    play(speak(menu, "en"))
    choice = input("Operator: enter language number: ").strip()
    lang_name, lang_code = LANGUAGES.get(choice, ("English", "en"))
    print(f"[Session] Language set to: {lang_name} ({lang_code})")
    return lang_name, lang_code

def run_intake(lang_name: str, lang_code: str) -> list:
    """Ask 5 intake questions in patient language. Return QA pairs in English."""
    qa_pairs = []

    greeting = translate(
        "Hello! I am MedRover. I will ask you a few questions before the doctor sees you.",
        "English", lang_name
    )
    play(speak(greeting, lang_code))

    for i, question_en in enumerate(INTAKE_QUESTIONS):
        # Translate question and speak it
        question_native = translate(question_en, "English", lang_name)
        print(f"\n[Intake Q{i+1}] {question_en}")
        print(f"[Intake Q{i+1} → {lang_name}] {question_native}")
        play(speak(question_native, lang_code))

        # Cue patient and record
        play(speak(translate("Please speak now.", "English", lang_name), lang_code))
        audio = record(seconds=8)

        # Transcribe in patient's language
        answer_native = transcribe(audio, language=lang_code)
        print(f"[Patient said ({lang_name})] {answer_native}")

        # Translate answer to English for summary
        answer_en = translate(answer_native, lang_name, "English")
        print(f"[Translated] {answer_en}")

        qa_pairs.append({"q": question_en, "a": answer_en})

    # Acknowledge completion
    done = translate("Thank you. Please wait while I prepare your information for the doctor.", "English", lang_name)
    play(speak(done, lang_code))

    return qa_pairs

def show_summary(summary: str):
    print("\n" + "="*50)
    print("PATIENT CLINICAL SUMMARY")
    print("="*50)
    print(summary)
    print("="*50 + "\n")

def doctor_relay(lang_name: str, lang_code: str):
    """
    Live bidirectional translation.
    D = doctor speaks English → patient hears in their language
    P = patient speaks → doctor reads English translation
    Q = end relay session
    """
    intro = translate("The doctor will speak with you now.", "English", lang_name)
    play(speak(intro, lang_code))

    print("\n[Relay Mode] D=Doctor speaks | P=Patient speaks | Q=Quit relay")

    while True:
        mode = input("Mode: ").strip().upper()

        if mode == "Q":
            break

        elif mode == "D":
            print("[Recording doctor...]")
            audio = record(seconds=8)
            text_en = transcribe(audio, language="en")
            print(f"[Doctor (EN)]: {text_en}")
            text_patient = translate(text_en, "English", lang_name)
            print(f"[→ {lang_name}]: {text_patient}")
            play(speak(text_patient, lang_code))

        elif mode == "P":
            print(f"[Recording patient ({lang_name})...]")
            audio = record(seconds=8)
            text_native = transcribe(audio, language=lang_code)
            print(f"[Patient ({lang_name})]: {text_native}")
            text_en = translate(text_native, lang_name, "English")
            print(f"[→ English for doctor]: {text_en}")
            play(speak(text_en, "en"))

def run_prescription(lang_name: str, lang_code: str, country: str = "Mexico"):
    """Capture prescription, look up medicines, speak results to patient."""
    prompt = translate(
        "Please hold the prescription up to the camera for a few seconds.",
        "English", lang_name
    )
    play(speak(prompt, lang_code))
    input("Operator: press Enter when prescription is in frame... ")

    results = run_prescription_flow(country=country)

    for item in results:
        msg = f"{item['medicine']}: {item['info']}"
        msg_native = translate(msg, "English", lang_name)
        print(f"[Prescription] {msg}")
        play(speak(msg_native, lang_code))

def main():
    patient_num = 1
    country = input("Enter target country for medicine lookup (e.g. Mexico, India): ").strip() or "Mexico"

    while True:
        print(f"\n{'='*50}")
        print(f"PATIENT {patient_num} — Waiting for detection")
        print(f"{'='*50}")

        # Detect patient
        detected = detect_face(timeout=20)
        if not detected:
            print("[Detection] No face detected. Skipping.")
        else:
            print("[Detection] Patient detected. Starting session.\n")

            # Language selection
            lang_name, lang_code = select_language()

            # Intake
            qa_pairs = run_intake(lang_name, lang_code)

            # Summary
            summary = generate_summary(qa_pairs)
            show_summary(summary)

            # Doctor relay
            input("\nOperator: press Enter when doctor is ready for relay... ")
            doctor_relay(lang_name, lang_code)

            # Prescription (optional)
            do_rx = input("\nRun prescription lookup? (y/n): ").strip().lower()
            if do_rx == "y":
                run_prescription(lang_name, lang_code, country=country)

        # Move to next patient
        next_p = input(f"\nMove to patient {patient_num + 1}? (y/n): ").strip().lower()
        if next_p == "y":
            move_forward(duration=2.0)
            patient_num += 1
        else:
            print("Session ended.")
            break

if __name__ == "__main__":
    main()
```

---

### requirements.txt
```
anthropic
opencv-python
pyaudio
easyocr
scrapegraph-py
requests
```

---

## 8. Team Split & 4-Hour Timeline

### Team Roles

| Person | Owns |
|---|---|
| A | Hardware: Pi setup, camera, audio I/O, navigation, Cyberwave |
| B | AI pipeline: STT + TTS + translation + nurse agent |
| C | Prescription: EasyOCR + ScrapeGraph |
| D (if 4th) | Integration: main.py state machine + demo polish |

---

### Hour 1 — Environment Setup + Individual Modules (0:00–1:00)

**0:00–0:20 — Everyone together**
- [ ] Create `medrover/` repo, set up `config.py` with all API keys
- [ ] `pip install anthropic opencv-python pyaudio easyocr scrapegraph-py requests` on Pi
- [ ] Verify Cyberwave Edge is running: `docker ps` on Pi
- [ ] Test USB mic: `arecord -d 3 test.wav && aplay test.wav`
- [ ] Test speaker: `aplay /usr/share/sounds/alsa/Front_Center.wav`
- [ ] Confirm camera connected: `python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"`

**0:20–1:00 — Split**
- **Person A:** Get `camera.py` detecting a face live. Get `audio.py` recording and playing back. Test navigation via Cyberwave.
- **Person B:** Get a full STT → translate → TTS round-trip working in isolation. Speak a Spanish phrase, transcribe it, translate to English, speak English back.
- **Person C:** Get EasyOCR reading text from a printed prescription photo. Get ScrapeGraph returning medicine info for a hardcoded medicine name.

**Milestone by 1:00:** Every module tested independently.

---

### Hour 2 — Core Flow Integration (1:00–2:00)

- Person A hands off working audio + camera modules
- Person B hands off working STT/TTS/translate functions
- Person D (or Person B) wires `main.py` state machine
- Run the full intake loop for one patient end-to-end
- Fix audio timing issues (recording duration, playback blocking)
- Verify smallest.ai voice IDs for each language from their dashboard

**Milestone by 2:00:** Full intake (5 questions → summary) works for Spanish-speaking patient.

---

### Hour 3 — Doctor Relay + Prescription + Navigation (2:00–3:00)

- **Person A:** Test rover movement on the actual floor. Tune forward duration for ~1 meter. Verify camera angle works for both face detection and prescription capture.
- **Person B:** Test doctor relay mode with a real conversation. Tune recording duration. Add "listening…" audio cue before each record call.
- **Person C:** Test prescription flow with a real printed prescription. Tune ScrapeGraph prompt if results are noisy. Add caching.
- **Person D:** Integrate prescription flow into `main.py`. Wire navigation call at end of each patient session.

**Milestone by 3:00:** Full end-to-end flow works for one patient including relay and prescription.

---

### Hour 4 — Two Demo Runs + Fallbacks + Polish (3:00–4:00)

**3:00–3:30 — Two full runs**
- Run Patient 1 (Spanish): full intake + relay + prescription
- Run Patient 2 (Hindi or French): intake + relay only

**3:30–4:00 — Fix and prepare demo**
- Lock in the demo script (see Section 9)
- Confirm all API keys are working
- Prepare printed prescription and test patient scripts

---

## 9. Fallback Plan

| Component Fails | Fallback |
|---|---|
| smallest.ai STT slow/down | `pip install openai-whisper` → `whisper.load_model("base").transcribe(audio_file)` — runs fully on Pi, 30+ languages |
| smallest.ai TTS down | `pip install gtts` → `gTTS(text, lang=lang_code).save("out.mp3")` → `mpg321 out.mp3` |
| ScrapeGraph rate limit | Hardcode medicine lookup results for the 2–3 demo medicines |
| Cyberwave navigation failing | Skip rover movement; demo the robot stationary — the AI is the product |
| Face detection unreliable | Replace `detect_face()` with a keyboard Enter press to start each session |

---

## 10. Demo Script (3 minutes)

```
[SETUP]
- 2 patients seated 1 meter apart
- Doctor standing to the side with laptop showing the terminal

[RUN]
1.  Rover faces Patient 1 (Spanish-speaking)
2.  Camera detects face → "Hello! Press 1 for Spanish..."
3.  Operator presses 1
4.  Rover asks 5 questions in Spanish, patient responds naturally
5.  Terminal displays clinical summary in English
6.  "The doctor will speak with you now"
7.  Doctor relay: D pressed → doctor speaks English → patient hears Spanish
8.  Patient speaks Spanish → doctor reads English on screen
9.  Printed prescription held to camera → rover says "Please hold prescription..."
10. OCR detects "Amoxicillin, Ibuprofen"
11. ScrapeGraph returns pricing → rover speaks results in Spanish to patient
12. Operator presses "move to next patient"
13. Rover moves forward ~1 meter → stops at Patient 2 → repeats
```

---

## 11. Why This Wins (Judging Framing)

This is not a translation app on wheels. It is an autonomous triage agent that closes a real operational gap in field medicine.

**The Perceive → Reason → Act loop:**
- **Perceive:** Camera (face detection, prescription image) + Microphone (patient speech)
- **Reason:** Claude (nurse agent, translation, clinical summary, medicine extraction) + ScrapeGraph (real-time medicine data)
- **Act:** Speak in patient's language + Display summary for doctor + Move to next patient

**The gap it closes:** In a field clinic with 30 patients and one doctor who speaks no Spanish, there is no LanguageLine phone, no interpreter, no pharmacist. MedRover handles pre-consultation intake autonomously, frees the doctor to focus on diagnosis, and gives every patient access to information about their own prescription — in their own language, in real time.

---

*Built for the Physical AI Track — Cyberwave × smallest.ai Hackathon*
