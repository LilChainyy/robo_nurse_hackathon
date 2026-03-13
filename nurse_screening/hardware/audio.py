"""
hardware/audio.py

Microphone recording (pyaudio) and speaker playback.
Playback is cross-platform: uses afplay on macOS, aplay on Linux (Pi).
"""

import io
import platform
import subprocess
import tempfile
import wave

import pyaudio

from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK

_FORMAT = pyaudio.paInt16


def record(seconds: int = 8) -> bytes:
    """
    Records audio from the default microphone for `seconds` seconds.
    Returns raw WAV bytes.
    """
    p = pyaudio.PyAudio()
    stream = p.open(
        format=_FORMAT,
        channels=AUDIO_CHANNELS,
        rate=AUDIO_SAMPLE_RATE,
        input=True,
        frames_per_buffer=AUDIO_CHUNK,
    )

    print(f"[Audio] Recording for {seconds}s...")
    frames = [
        stream.read(AUDIO_CHUNK)
        for _ in range(int(AUDIO_SAMPLE_RATE / AUDIO_CHUNK * seconds))
    ]
    print("[Audio] Recording done.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(AUDIO_CHANNELS)
        wf.setsampwidth(p.get_sample_size(_FORMAT))
        wf.setframerate(AUDIO_SAMPLE_RATE)
        wf.writeframes(b"".join(frames))

    return buf.getvalue()


def play(audio_bytes: bytes):
    """
    Plays WAV audio bytes through the default speaker.
    Uses afplay on macOS, aplay on Linux.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["afplay", tmp_path], check=True)
        else:
            # Linux / Raspberry Pi
            result = subprocess.run(["aplay", tmp_path], check=False)
            if result.returncode != 0:
                # Fallback: try ffplay (comes with ffmpeg)
                subprocess.run(
                    ["ffplay", "-nodisp", "-autoexit", tmp_path],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except FileNotFoundError as e:
        print(f"[Audio] Playback command not found: {e}. Audio skipped.")
