"""Experimental offline OCR for the hotel's specific two-week form.

Packs Tesseract in the Windows installer. Fixed-position text extraction is a
first pass, not suitable for unattended payroll. Every sheet is human approved.
"""
from __future__ import annotations
import os
import sys
import re
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import pytesseract
from .core import Sheet, ShiftDay, DISPLAY, digest_bytes, normalize_time
from .handwriting import recognize_time

REF_W, REF_H = 958, 1350
# Measured from the user-supplied paper form. Rows of the form (not phone calendar days).
ROW_Y = [(368 + 39*i, 405 + 39*i) for i in range(7)] + [(673 + 38*i, 712 + 38*i) for i in range(7)]
# Image coordinate columns: day/date, Time In, Time Out, Time In, Time Out, Total.
COL_X = ((218, 338), (347, 463), (480, 600), (610, 731))
# Source form's printed 'Time In' starts at x~=213 (content area x=215-345)
# Actual 1st time-in x=212-347; first time-out x=347-478.
COL_X = ((215, 342), (350, 474), (479, 602), (612, 738))


def configure_tesseract() -> None:
    # For a packaged executable, include Tesseract next to app's internal files.
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    paths = [root / "tesseract" / "tesseract.exe",
             Path(sys.executable).parent / "tesseract" / "tesseract.exe",
             Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Tesseract-OCR" / "tesseract.exe"]
    for candidate in paths:
        if candidate.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            os.environ["TESSDATA_PREFIX"] = str(candidate.parent / "tessdata")
            return
    # Linux/macOS development use PATH.


def load_pages(path: str) -> list[Image.Image]:
    if path.lower().endswith(".pdf"):
        import fitz
        doc = fitz.open(path)
        images = []
        try:
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        finally:
            doc.close()
        return images
    with Image.open(path) as im:
        return [ImageOps.exif_transpose(im).convert("RGB")]


def _crop_scaled(im: Image.Image, rect: tuple[int, int, int, int]) -> Image.Image:
    x1, y1, x2, y2 = rect
    # Convert portrait scan to known sample paper proportions. Scanner apps
    # generally deskew when capturing; perspective correction isn't assumed.
    return im.crop((int(x1*im.width/REF_W), int(y1*im.height/REF_H),
                    int(x2*im.width/REF_W), int(y2*im.height/REF_H)))


def _likely_blank(image: Image.Image) -> bool:
    """Conservative empty-cell short-circuit to avoid OCR calls for blank cells.

    Ignore the outer 4 pixels where printed grid lines may intrude. If any
    obvious dark or colored handwriting remains, OCR is still attempted.
    False blanks are still possible on pale pencil/low-quality photos: all
    readings are provisional and require manager verification.
    """
    w, h = image.size
    if h < 10 or w < 10:
        return False
    interior = image.convert('RGB').crop((4, 4, w-4, h-4))
    blue_count, dark_count = 0, 0
    pixels = interior.get_flattened_data() if hasattr(interior, 'get_flattened_data') else interior.getdata()
    for r, g, b in pixels:
        if b-r > 22 and b-g > 8 and b < 245:
            blue_count += 1
        if r < 150 and g < 150 and b < 150:
            dark_count += 1
        if blue_count >= 9 or dark_count >= 14:
            return False
    return True


def _ocr_cell(image: Image.Image, characters: str) -> str:
    img = ImageOps.grayscale(image)
    img = ImageOps.autocontrast(img)
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = img.resize((max(50, img.width * 3), max(40, img.height * 3)), Image.Resampling.LANCZOS)
    config = f"--psm 7 -c tessedit_char_whitelist={characters}"
    return pytesseract.image_to_string(img, config=config).strip().replace("\n", " ")[:35]


def _cleanup_time(text: str) -> str:
    cleaned = re.sub(r"[^0-9APMapm:]", "", text).upper().replace("M", "")
    return cleaned[:12]


def scan_page(path: str, image: Image.Image, page_number: int = 1) -> Sheet:
    raw = Path(path).read_bytes()
    fingerprint = digest_bytes(raw + f"-page{page_number}".encode())
    sheet = Sheet(source=f"{path}#page{page_number}", source_hash=fingerprint)
    configure_tesseract()
    # Real photographs supplied in November 2026 use a DIFFERENT printed sheet:
    # one in/out pair, date and rooms columns, no AM/PM. Do not use legacy boxes.
    from .photo_form import is_this_form, scan_this_form
    if is_this_form(image):
        scan_this_form(sheet, image)
        return sheet
    # Every recognition result is tentative until the manager approves the sheet.
    name_area = _crop_scaled(image, (593, 204, 888, 249))
    guess = _ocr_cell(name_area, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    # Tesseract often removes spaces from full names; recover CamelCase word boundaries.
    guess = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", guess)
    sheet.employee = guess if len(guess.strip()) >= 3 else ""
    warnings = ["OCR is preliminary. Verify every punch against the photo before approving."]
    for idx, (top, bottom) in enumerate(ROW_Y):
        day = ShiftDay()
        for field, (left, right) in zip(("in1", "out1", "in2", "out2"), COL_X):
            cell = _crop_scaled(image, (left, top + 3, right, bottom - 3))
            if _likely_blank(cell):
                guess = ""
            else:
                # Blue-ink handwritten-digit model is conservative: it only
                # supplies an answer when every character is high confidence.
                # It is a preliminary entry, never approved payroll.
                suggestion, confidence, status = recognize_time(cell)
                if suggestion:
                    guess = suggestion
                else:
                    guess = _cleanup_time(_ocr_cell(cell, "0123456789:APMapm"))
                    if status not in ('no-visible-blue-ink', 'ok'):
                        warnings.append(
                            f"Week {idx//7+1} {DISPLAY[idx%7]}, {field}: "
                            f"handwriting model abstained ({status}); check photograph")
            day.recognized[field] = guess
            # Never place unreadable/ambiguous OCR into trusted payroll entries.
            if guess and not normalize_time(guess)[1]:
                setattr(day, field, guess)
            elif not _likely_blank(cell):
                warnings.append(f"Week {idx//7+1} {DISPLAY[idx%7]}, {field}: writing present but OCR could not read a valid time")
        sheet.days[idx] = day
    sheet.scan_warnings = warnings
    return sheet
