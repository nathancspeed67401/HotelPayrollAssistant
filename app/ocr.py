"""Offline aligned whole-entry OCR for the hotel's two-week form.

Every suggestion remains provisional until all rows are visually reviewed.
"""
from __future__ import annotations
import os
import sys
import re
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
import pytesseract
from .core import Sheet, DISPLAY, TIME_FIELDS, digest_bytes
from .handwriting import recognize_time
from .form_geometry import REF_W, REF_H, ROW_Y, COL_X, find_form_grid
from .line_ocr import Reading, LineOCRError, choose_time, get_recognizer


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
    # The actual Comfort Suites sheet has one pair; retain the aligned
    # two-pair reader for the older form instead of replacing either reader.
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
    grid = find_form_grid(image)
    if grid is None:
        warnings.append('Printed grid could not be aligned reliably. Check that each punch belongs to the correct row and column.')
        for idx,day in enumerate(sheet.days):
            for field in TIME_FIELDS:
                day.observations[field] = {'status':'alignment-failed','raw':''}
            warnings.append(f'Week {idx//7+1} {DISPLAY[idx%7]}, grid not aligned: read the full photograph')
        sheet.scan_warnings = warnings
        return sheet
    for row in range(14):
        quad = sum((grid.cell_quad(row,col) for col in range(4)),())
        sheet.review_boxes.append([max(0,round(min(x for x,y in quad)-30)),
                                   max(0,round(min(y for x,y in quad)-4)),
                                   min(image.width,round(max(x for x,y in quad)+4)),
                                   min(image.height,round(max(y for x,y in quad)+4))])
    cells = []
    for idx, (top, bottom) in enumerate(ROW_Y):
        for col, (field, (left, right)) in enumerate(zip(TIME_FIELDS, COL_X)):
            fixed = _crop_scaled(image, (left, top + 3, right, bottom - 3))
            cell = grid.crop_cell(image, idx, col) if grid else fixed
            cells.append((idx, field, cell, fixed, _likely_blank(cell)))
    active = [cell for cell in cells if not cell[4]]
    line_readings = [[] for _ in active]
    if active:
        try:
            line_readings = get_recognizer().recognize([cell[2] for cell in active])
        except LineOCRError as exc:
            warnings.append(f'{exc}. Enter unread punches from the photo.')
    for (idx, field, cell, fixed, _), readings in zip(active, line_readings):
        # The small digit model supplies conservative suggestions and flags
        # plausible conflicting readings from the aligned and legacy crops.
        for source, crop in [('digits-grid', cell)] + ([('digits-fixed', fixed)] if grid else []):
            text, confidence, _status = recognize_time(crop, minimum_confidence=.60)
            if text:
                readings.append(Reading(text, confidence, confidence, source))
        decision = choose_time(readings)
        sheet.days[idx].recognized[field] = decision.raw
        sheet.days[idx].observations[field] = {'status':decision.status,'raw':decision.raw,
                                             'confidence_is_calibrated':False}
        if decision.value:
            setattr(sheet.days[idx], field, decision.value)
        else:
            detail = f' (read: {decision.raw[:60]})' if decision.raw else ''
            reason = {'conflicting-readings': 'different possible times',
                      'uncertain-reading': 'uncertain time',
                      'unreadable-or-missing-AM/PM': 'unreadable time or missing AM/PM'}[decision.status]
            warnings.append(f'Week {idx//7+1} {DISPLAY[idx%7]}, {field}: writing needs review — {reason}{detail}')
    for idx, field, _cell, _fixed, blank in cells:
        if blank:
            sheet.days[idx].recognized[field] = ''
            sheet.days[idx].observations[field] = {'status':'blank','raw':''}
    sheet.scan_warnings = warnings
    return sheet
