"""
hardware/camera.py

Face detection via OpenCV Haar Cascade and image capture.
Works on both macOS (dev) and Raspberry Pi (production).
"""

import time
import cv2

_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def detect_face(timeout: int = 15) -> bool:
    """
    Opens the default camera and returns True as soon as a face is detected.
    Returns False if no face is found within `timeout` seconds.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Camera] WARNING: Could not open camera. Skipping face detection.")
        return False

    print(f"[Camera] Scanning for face (timeout={timeout}s)...")
    deadline = time.time() + timeout

    while time.time() < deadline:
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = _face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(80, 80)
        )
        if len(faces) > 0:
            cap.release()
            print("[Camera] Face detected.")
            return True

    cap.release()
    print("[Camera] No face detected within timeout.")
    return False


def capture_image(path: str = "/tmp/prescription.jpg") -> str:
    """
    Captures a single frame and saves it to `path`.
    Returns the file path on success, empty string on failure.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Camera] WARNING: Could not open camera for capture.")
        return ""

    ret, frame = cap.read()
    cap.release()

    if ret:
        cv2.imwrite(path, frame)
        print(f"[Camera] Image saved to {path}")
        return path

    print("[Camera] WARNING: Failed to capture frame.")
    return ""
