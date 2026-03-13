"""
hardware/navigation.py

Rover movement via Cyberwave Edge Runtime (HTTP on localhost:8080).

NOTE: The exact endpoint paths depend on your Cyberwave Edge version.
Confirm from the Cyberwave dashboard or SDK docs once the edge runtime
is running on the Pi:  docker ps  →  curl http://localhost:8080/

Current assumption: POST /robot/move with {linear, angular, duration}
Update CYBERWAVE_EDGE_URL and endpoint below if different.
"""

import requests

from config import CYBERWAVE_EDGE_URL

_MOVE_ENDPOINT = f"{CYBERWAVE_EDGE_URL}/robot/move"
_TIMEOUT       = 5  # seconds


def move_forward(duration: float = 2.0, speed: float = 0.3):
    """
    Move the rover forward for `duration` seconds at `speed` m/s.
    Safe to call with duration=0 in tests (no-op effectively).
    """
    if duration <= 0:
        return
    _send_move(linear=speed, angular=0.0, duration=duration)


def stop():
    """Immediately stop the rover."""
    _send_move(linear=0.0, angular=0.0, duration=0)


def turn(degrees: float, speed: float = 0.5):
    """
    Turn the rover by `degrees` (positive = left, negative = right).
    Duration is estimated from degrees; tune as needed on the physical rover.
    """
    duration = abs(degrees) / 90.0  # rough estimate: 90° ≈ 1 second at speed 0.5
    angular  = speed if degrees > 0 else -speed
    _send_move(linear=0.0, angular=angular, duration=duration)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _send_move(linear: float, angular: float, duration: float):
    try:
        resp = requests.post(
            _MOVE_ENDPOINT,
            json={"linear": linear, "angular": angular, "duration": duration},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        print(f"[Navigation] linear={linear} angular={angular} duration={duration}s")
    except requests.ConnectionError:
        print(f"[Navigation] WARNING: Cyberwave Edge not reachable at {CYBERWAVE_EDGE_URL}. "
              "Is the Docker container running?")
    except requests.RequestException as e:
        print(f"[Navigation] Move failed: {e}")
