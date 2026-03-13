import os
from dotenv import load_dotenv

load_dotenv()

SMALLEST_API_KEY    = os.environ.get("SMALLEST_API_KEY", "")
CLAUDE_API_KEY      = os.environ.get("CLAUDE_API_KEY", "")
OPENAI_API_KEY      = os.environ.get("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY   = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID  = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
ELEVENLABS_STT_MODEL = os.environ.get("ELEVENLABS_STT_MODEL", "scribe_v1")
DEEPL_API_KEY       = os.environ.get("DEEPL_API_KEY", "")
SCRAPEGRAPH_API_KEY = os.environ.get("SCRAPEGRAPH_API_KEY", "")

# MongoDB
MONGODB_URI      = os.environ.get("MONGODB_URI", "")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "medrover")

# Rover settings
CYBERWAVE_EDGE_URL  = os.environ.get("CYBERWAVE_EDGE_URL", "http://localhost:8080")

# Audio settings
AUDIO_SAMPLE_RATE   = 16000
AUDIO_CHANNELS      = 1
AUDIO_CHUNK         = 1024
RECORDING_SECONDS   = 8   # default patient/doctor recording window

# Session defaults
DEFAULT_PATIENT_LANG_CODE = "es"
DEFAULT_PATIENT_LANG_NAME = "Spanish"
DEFAULT_COUNTRY           = "Mexico"
