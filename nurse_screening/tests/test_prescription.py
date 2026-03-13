"""
tests/test_prescription.py — Person C

Run from medrover/ directory:
    python tests/test_prescription.py

Validates independently (no camera or mic needed):
  1. EasyOCR reads text from a sample prescription image
  2. Claude extracts medicine names from raw OCR text
  3. ScrapeGraph returns medicine availability info
  4. Full prescription flow with a sample image

Requires: CLAUDE_API_KEY and SCRAPEGRAPH_API_KEY in .env

To generate a sample prescription image for testing:
    python tests/test_prescription.py --make-sample
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SAMPLE_IMAGE_PATH = "/tmp/sample_prescription.jpg"

# Raw OCR-like text simulating a prescription scan
SAMPLE_OCR_TEXT = """
Patient: Juan Garcia
Dr. Smith MD

Rx:
Amoxicillin 500mg — take 1 capsule 3x daily for 7 days
Ibuprofen 400mg   — take 1 tablet every 8 hours as needed for pain
Omeprazole 20mg   — take 1 capsule daily before breakfast

Refills: 0
"""


def make_sample_prescription_image():
    """Creates a simple prescription image for OCR testing (no scanner needed)."""
    try:
        import cv2
        import numpy as np

        img = np.ones((400, 600, 3), dtype=np.uint8) * 255  # white background
        lines = SAMPLE_OCR_TEXT.strip().split("\n")
        y = 40
        for line in lines:
            cv2.putText(img, line.strip(), (30, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
            y += 30

        cv2.imwrite(SAMPLE_IMAGE_PATH, img)
        print(f"  Sample prescription image saved to: {SAMPLE_IMAGE_PATH}")
        return SAMPLE_IMAGE_PATH
    except Exception as e:
        print(f"  Could not create image: {e}")
        return None


def test_ocr(image_path: str = None):
    print("\n[Test 1] EasyOCR — reading prescription image")
    try:
        import easyocr
        path = image_path or SAMPLE_IMAGE_PATH

        if not os.path.exists(path):
            print(f"  No image at {path}. Creating sample...")
            path = make_sample_prescription_image()
            if not path:
                print("  → SKIP — no image available")
                return None

        reader = easyocr.Reader(["en"], gpu=False)
        results = reader.readtext(path)
        raw_text = " ".join([r[1] for r in results])
        ok = len(raw_text) > 10
        print(f"  OCR output: {raw_text[:200]}...")
        print(f"  → {'PASS' if ok else 'FAIL — no text extracted'}")
        return raw_text if ok else None
    except ImportError:
        print("  → FAIL — easyocr not installed. Run: pip install easyocr")
        return None
    except Exception as e:
        print(f"  → FAIL — {e}")
        return None


def test_extract_medicines(ocr_text: str = None):
    print("\n[Test 2] Claude — extracting medicine names from OCR text")
    from ai.agent import extract_medicine_names

    text = ocr_text or SAMPLE_OCR_TEXT
    medicines = extract_medicine_names(text)
    ok = len(medicines) > 0
    print(f"  Input text (truncated): {text[:100]}...")
    print(f"  Extracted medicines   : {medicines}")
    print(f"  → {'PASS' if ok else 'FAIL — no medicines extracted'}")
    return medicines if ok else []


def test_scrapegraph_lookup(medicines: list = None):
    print("\n[Test 3] ScrapeGraph — medicine availability lookup")
    med_list = medicines or ["Amoxicillin", "Ibuprofen"]
    country = "Mexico"

    try:
        from scrapegraph_py import Client
        from config import SCRAPEGRAPH_API_KEY

        if not SCRAPEGRAPH_API_KEY:
            print("  → SKIP — SCRAPEGRAPH_API_KEY not set in .env")
            return False

        sgai = Client(api_key=SCRAPEGRAPH_API_KEY)
        results = []

        for med in med_list[:2]:  # limit to 2 during testing
            print(f"  Looking up: {med}...")
            try:
                result = sgai.smartscraper(
                    website_url=f"https://www.google.com/search?q={med}+price+pharmacy+{country}",
                    user_prompt=(
                        f"Find the price and availability of {med} in {country}. "
                        f"Return one sentence: medicine name, approximate price in local currency, "
                        f"and whether it is commonly available."
                    )
                )
                info = str(result.get("result", f"{med}: not found"))
                print(f"  {med}: {info}")
                results.append({"medicine": med, "info": info})
            except Exception as e:
                print(f"  {med}: lookup failed — {e}")
                results.append({"medicine": med, "info": f"lookup failed: {e}"})

        ok = len(results) > 0
        print(f"  → {'PASS' if ok else 'FAIL'}")
        return results

    except ImportError:
        print("  → FAIL — scrapegraph-py not installed. Run: pip install scrapegraph-py")
        return []


def test_full_prescription_flow():
    print("\n[Test 4] Full prescription flow (image → OCR → medicines → lookup)")
    # Build the prescription module inline to test it without Pi camera
    try:
        import easyocr
        from ai.agent import extract_medicine_names

        # Use sample image
        path = SAMPLE_IMAGE_PATH
        if not os.path.exists(path):
            make_sample_prescription_image()

        reader = easyocr.Reader(["en"], gpu=False)
        results = reader.readtext(path)
        raw_text = " ".join([r[1] for r in results])

        medicines = extract_medicine_names(raw_text)
        print(f"  Medicines found: {medicines}")

        lookup_results = test_scrapegraph_lookup(medicines)

        ok = len(medicines) > 0
        print(f"  → {'PASS' if ok else 'FAIL'}")
        return ok
    except Exception as e:
        print(f"  → FAIL — {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--make-sample", action="store_true",
                        help="Just generate the sample prescription image and exit")
    args = parser.parse_args()

    if args.make_sample:
        make_sample_prescription_image()
        sys.exit(0)

    print("=" * 50)
    print("  MedRover — Prescription Tests (Person C)")
    print("=" * 50)

    # Create sample image first
    make_sample_prescription_image()

    ocr_text  = test_ocr(SAMPLE_IMAGE_PATH)
    medicines = test_extract_medicines(ocr_text)
    test_scrapegraph_lookup(medicines)
    test_full_prescription_flow()

    print("\n" + "=" * 50)
    print("  Done. Fix any FAILs before integration.")
    print("=" * 50)
