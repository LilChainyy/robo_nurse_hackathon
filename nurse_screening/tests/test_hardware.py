"""
tests/test_hardware.py — Person A

Run from medrover/ directory:
    python tests/test_hardware.py

Validates independently:
  1. Camera opens and face detection triggers
  2. Microphone records audio
  3. Speaker plays back recorded audio
  4. Navigation stub (no rover needed to pass this)

Each test prints PASS / FAIL so you know exactly what's working.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_camera_open():
    print("\n[Test 1] Camera — can it open?")
    import cv2
    cap = cv2.VideoCapture(0)
    opened = cap.isOpened()
    cap.release()
    status = "PASS" if opened else "FAIL (no camera detected)"
    print(f"  → {status}")
    return opened


def test_face_detection():
    print("\n[Test 2] Face detection — look at the camera now...")
    from hardware.camera import detect_face
    found = detect_face(timeout=10)
    status = "PASS — face detected" if found else "FAIL — no face within 10s"
    print(f"  → {status}")
    return found


def test_microphone():
    print("\n[Test 3] Microphone — recording 3 seconds of audio...")
    from hardware.audio import record
    audio = record(seconds=3)
    ok = len(audio) > 1000  # anything reasonable
    status = f"PASS — captured {len(audio)} bytes" if ok else "FAIL — no audio captured"
    print(f"  → {status}")
    return audio if ok else None


def test_playback(audio: bytes):
    print("\n[Test 4] Speaker — playing back what was just recorded...")
    if not audio:
        print("  → SKIP — no audio from microphone test")
        return False
    from hardware.audio import play
    try:
        play(audio)
        print("  → PASS — if you heard the playback, audio I/O is working")
        return True
    except Exception as e:
        print(f"  → FAIL — {e}")
        return False


def test_navigation_stub():
    print("\n[Test 5] Navigation stub — no rover needed")
    try:
        # Just confirm the module can be imported and called without crashing
        import importlib, types
        # navigation.py may not exist yet; create a soft check
        try:
            from hardware.navigation import move_forward, stop
            move_forward(duration=0)  # zero duration = no actual movement
            stop()
            print("  → PASS — navigation module loaded and callable")
        except ImportError:
            print("  → SKIP — hardware/navigation.py not written yet (expected)")
        return True
    except Exception as e:
        print(f"  → FAIL — {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("  MedRover — Hardware Tests (Person A)")
    print("=" * 50)

    test_camera_open()
    test_face_detection()
    audio = test_microphone()
    test_playback(audio)
    test_navigation_stub()

    print("\n" + "=" * 50)
    print("  Done. Fix any FAILs before integration.")
    print("=" * 50)
