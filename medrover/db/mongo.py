"""
db/mongo.py

MongoDB persistence for MedRover patient sessions.
Collection: medrover.nurse_summary

Document schema:
{
    session_id          str       — uuid4
    name                str       — patient name collected at session start
    checked_in_at       datetime  — when nurse screening started
    language_code       str       — e.g. "es"
    language_name       str       — e.g. "Spanish"

    # Structured fields extracted by GPT-4o
    chief_complaint     str
    symptoms            [str]
    pain_level          int       — patient-reported (1–10)
    allergies           [str]
    current_medications [str]
    severity_score      int       — clinical risk score (1–10), GPT-4o assessed
    risk_level          str       — "low" | "medium" | "high" | "critical"

    # Full conversation logs
    conversation_english  [{"role": "nurse"|"patient", "text": str}]
    conversation_native   [{"role": "nurse"|"patient", "text": str}]  # audit

    # Doctor-facing output
    clinical_summary    str       — formatted intake note in English

    status              str       — "waiting" | "with_doctor" | "done"
    created_at          datetime
    updated_at          datetime
}
"""

import re
from datetime import datetime, timezone

from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection

from config import MONGODB_URI, MONGODB_DATABASE

_COLLECTION = "nurse_summary"

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

_client: MongoClient | None = None


def _get_collection() -> Collection:
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI)
    return _client[MONGODB_DATABASE][_COLLECTION]


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def save_patient_session(
    name: str,
    language_code: str,
    language_name: str,
    english_log: list[dict],
    native_log: list[dict],
    structured: dict,
    clinical_summary: str,
) -> str:
    """
    Inserts a completed nurse intake session into MongoDB.

    Returns the session_id string (e.g. "P001").
    """
    count      = _get_collection().count_documents({})
    session_id = f"P{count + 1:03d}"
    now = datetime.now(timezone.utc)

    doc = {
        "session_id":           session_id,
        "name":                 name,
        "checked_in_at":        now,
        "language_code":        language_code,
        "language_name":        language_name,

        # Structured clinical fields
        "chief_complaint":      structured.get("chief_complaint", ""),
        "symptoms":             structured.get("symptoms", []),
        "pain_level":           structured.get("pain_level", 0),
        "allergies":            structured.get("allergies", []),
        "current_medications":  structured.get("current_medications", []),
        "severity_score":       structured.get("severity_score", 0),
        "risk_level":           structured.get("risk_level", "unknown"),

        # Conversation logs
        "conversation_english": english_log,
        "conversation_native":  native_log,

        # Doctor summary
        "clinical_summary":     clinical_summary,

        "status":               "waiting",
        "created_at":           now,
        "updated_at":           now,
    }

    _get_collection().insert_one(doc)
    print(f"[DB] Session saved — id={session_id}, patient={name}, "
          f"severity={structured.get('severity_score')}, "
          f"risk={structured.get('risk_level')}")
    return session_id


def update_status(session_id: str, status: str):
    """Updates the status field for a session (waiting → with_doctor → done)."""
    _get_collection().update_one(
        {"session_id": session_id},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
    )


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_priority_queue() -> list[dict]:
    """
    Returns all waiting patients sorted by severity_score descending.
    Each entry includes: name, chief_complaint, severity_score, risk_level,
    checked_in_at, session_id.
    """
    col = _get_collection()
    patients = list(
        col.find(
            {"status": "waiting"},
            {
                "_id": 0,
                "session_id": 1,
                "name": 1,
                "chief_complaint": 1,
                "symptoms": 1,
                "severity_score": 1,
                "risk_level": 1,
                "pain_level": 1,
                "checked_in_at": 1,
            },
        ).sort("severity_score", DESCENDING)
    )
    return patients


def get_all_waiting() -> list[dict]:
    """Returns full documents for all waiting patients, sorted by severity descending."""
    return list(
        _get_collection()
        .find({"status": "waiting"}, {"_id": 0})
        .sort("severity_score", DESCENDING)
    )


def get_session(session_id: str) -> dict | None:
    """Returns the full document for a given session_id."""
    return _get_collection().find_one({"session_id": session_id}, {"_id": 0})


def search_by_name(name: str) -> list[dict]:
    """
    Case-insensitive partial name search.
    e.g. "juan" matches "Juan Garcia".
    Returns summary-level fields (no conversation logs).
    """
    pattern = re.compile(re.escape(name), re.IGNORECASE)
    return list(
        _get_collection().find(
            {"name": {"$regex": pattern}},
            {
                "_id": 0,
                "session_id": 1,
                "name": 1,
                "chief_complaint": 1,
                "symptoms": 1,
                "severity_score": 1,
                "risk_level": 1,
                "pain_level": 1,
                "status": 1,
                "checked_in_at": 1,
            },
        ).sort("checked_in_at", DESCENDING)
    )


# ---------------------------------------------------------------------------
# Display helper (terminal)
# ---------------------------------------------------------------------------

def print_priority_queue():
    """Prints a formatted priority queue to the terminal for the doctor."""
    patients = get_priority_queue()

    if not patients:
        print("\n  [Queue] No patients waiting.")
        return

    print("\n" + "=" * 60)
    print("  PATIENT PRIORITY QUEUE")
    print("=" * 60)
    print(f"  {'#':<3} {'Name':<20} {'Risk':<10} {'Score':<7} {'Chief Complaint'}")
    print("-" * 60)

    risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    patients.sort(key=lambda p: (
        risk_order.get(p.get("risk_level", "unknown"), 4),
        -p.get("severity_score", 0),
    ))

    for i, p in enumerate(patients, start=1):
        risk  = p.get("risk_level", "?").upper()
        score = p.get("severity_score", "?")
        name  = p.get("name", "Unknown")[:18]
        cc    = p.get("chief_complaint", "")[:30]
        print(f"  {i:<3} {name:<20} {risk:<10} {score:<7} {cc}")

    print("=" * 60)
