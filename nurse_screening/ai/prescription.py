"""
ai/prescription.py

Full prescription flow:
  1. Capture image from camera  (or accept a pre-captured path)
  2. EasyOCR extracts raw text
  3. Claude extracts medicine names
  4. ScrapeGraph looks up price + availability per medicine

Designed so Person C can test steps 2–4 without any hardware.
"""

import easyocr
from scrapegraph_py import Client

from ai.agent  import extract_medicine_names
from config    import SCRAPEGRAPH_API_KEY

_reader = None   # lazy-load: EasyOCR takes ~10s to initialise
_sgai   = None

_medicine_cache: dict[str, str] = {}


def _get_reader():
    global _reader
    if _reader is None:
        print("[Prescription] Loading EasyOCR model (first-time, ~10s)...")
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def _get_sgai():
    global _sgai
    if _sgai is None:
        _sgai = Client(api_key=SCRAPEGRAPH_API_KEY)
    return _sgai


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ocr_image(image_path: str) -> str:
    """
    Runs EasyOCR on `image_path` and returns the raw text string.
    """
    results = _get_reader().readtext(image_path)
    raw_text = " ".join(r[1] for r in results)
    print(f"[Prescription] OCR raw text: {raw_text[:200]}")
    return raw_text


def lookup_medicines(medicines: list[str], country: str = "Mexico") -> list[dict]:
    """
    Looks up price and availability for each medicine name via ScrapeGraph.
    Returns list of {"medicine": str, "info": str}.
    """
    sgai = _get_sgai()
    output = []

    for med in medicines:
        if med in _medicine_cache:
            info = _medicine_cache[med]
            print(f"[Prescription] {med} (cached): {info}")
        else:
            try:
                result = sgai.smartscraper(
                    website_url=(
                        f"https://www.google.com/search?q={med}+price+pharmacy+{country}"
                    ),
                    user_prompt=(
                        f"Find the price and availability of {med} in {country}. "
                        f"Return one sentence with: medicine name, approximate price "
                        f"in local currency, and whether it is commonly available."
                    ),
                )
                info = str(result.get("result", f"{med}: information not found"))
            except Exception as e:
                info = f"{med}: lookup failed ({e})"

            print(f"[Prescription] {med}: {info}")
            _medicine_cache[med] = info

        output.append({"medicine": med, "info": info})

    return output


def run_prescription_flow(country: str = "Mexico",
                          image_path: str = None) -> list[dict]:
    """
    Full flow. If `image_path` is None, captures from the rover camera.

    Returns:
        List of {"medicine": str, "info": str} dicts.
    """
    if image_path is None:
        from hardware.camera import capture_image
        print("[Prescription] Capturing prescription from camera...")
        image_path = capture_image()
        if not image_path:
            print("[Prescription] ERROR: Camera capture failed.")
            return []

    raw_text  = ocr_image(image_path)
    medicines = extract_medicine_names(raw_text)
    print(f"[Prescription] Detected medicines: {medicines}")

    if not medicines:
        print("[Prescription] No medicines detected in image.")
        return []

    return lookup_medicines(medicines, country=country)
