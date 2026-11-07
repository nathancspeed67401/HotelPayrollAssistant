"""Photo-form OCR for the hotel's actual single-pair Comfort Suites paper sheet.

Camera alignment and reading suggestions are experimental. No AM/PM is guessed.
Never distribute private employee timesheet photographs with the repository.
"""
from __future__ import annotations
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps, ImageEnhance

FORM_ID = "comfort_suites_single_pair"
PAGE_W, PAGE_H = 1000, 1470
NAME = (99, 247, 408, 298)
PUNCH_COLUMNS = {"in1": (280, 407), "out1": (410, 536)}
ROW_BOUNDS = ((355, 406), (406, 451), (451, 500), (500, 549),
              (549, 600), (600, 654), (654, 709),
              (775, 823), (823, 871), (871, 919), (919, 966),
              (966, 1011), (1011, 1057), (1057, 1102))


def _paper_box(image: Image.Image) -> tuple[int, int, int, int]:
    """Find pale paper against a colored table; use full image on uncertainty."""
    rgb = np.asarray(ImageOps.exif_transpose(image).convert('RGB'))
    h, w = rgb.shape[:2]
    scale = min(1.0, 1000.0 / max(h, w))
    small = cv2.resize(rgb, (max(1, round(w * scale)), max(1, round(h * scale))),
                       interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB)
    mask = np.uint8((hsv[:, :, 1] < 30) & (lab[:, :, 0] > 105)) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return (0, 0, w, h)
    largest = max(contours, key=cv2.contourArea)
    x, y, cw, ch = cv2.boundingRect(largest)
    sh, sw = mask.shape
    if (cv2.contourArea(largest) / (sw * sh) < .40 or
            cw < .65 * sw or ch < .45 * sh):
        return (0, 0, w, h)
    x1 = 0 if x < .06 * sw else x
    x2 = sw if x + cw > .94 * sw else x + cw
    return (max(0, round(x1 / scale)), max(0, round(y / scale)),
            min(w, round(x2 / scale)), min(h, round((y + ch) / scale)))


def normalized_page(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert('RGB')
    if image.width > image.height:
        image = image.rotate(90, expand=True)
    return image.crop(_paper_box(image)).resize((PAGE_W, PAGE_H), Image.Resampling.LANCZOS)


def _header_matches(page: Image.Image) -> bool:
    """Recognize form labels, independent of whether EXIF got orientation right."""
    top = ImageOps.autocontrast(ImageOps.grayscale(page.crop((70, 100, 940, 360))), cutoff=1)
    flat = re.sub(r'[^A-Z ]', ' ', pytesseract.image_to_string(top, config='--psm 6').upper())
    return (('SALINA SOUTH' in flat or 'SCHILLING RD' in flat or
             'ROOMS' in flat or 'ALOTTED' in flat) and
            ('TIME' in flat or 'PAY PERIOD' in flat or 'MANAGER' in flat))


def is_this_form(image: Image.Image) -> bool:
    """Find real form even when camera EXIF has left the photograph upside-down."""
    page = normalized_page(image)
    return _header_matches(page) or _header_matches(page.rotate(180))


def _row_transform(page: Image.Image) -> tuple[float, int]:
    """Fit the vertical grid to camera tilt/cropping using printed rules."""
    g = cv2.cvtColor(np.asarray(page), cv2.COLOR_RGB2GRAY)
    grad = cv2.Sobel(cv2.GaussianBlur(g, (3, 3), 0), cv2.CV_32F, 0, 1, ksize=3)
    mask = np.uint8(np.abs(grad) > 17) * 255
    lines = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (90, 1)))
    profile = np.convolve((lines[:, 80:930] > 0).sum(axis=1).astype(float),
                          np.ones(5), mode='same')
    marks = np.asarray([294, 355, 406, 451, 500, 549, 600, 654, 709,
                        775, 823, 871, 919, 966, 1011, 1057, 1102])
    best = (0.0, 1.0, 0)
    for scale in np.arange(.88, 1.14, .01):
        ys = marks * scale
        for shift in range(-230, 191, 2):
            pts = np.rint(ys + shift).astype(int)
            if pts.min() < 30 or pts.max() >= len(profile) - 20:
                continue
            score = float(profile[pts].sum())
            if score > best[0]:
                best = (score, float(scale), int(shift))
    if best[0] < 4000:
        return 1.0, 0
    return best[1], best[2]


def field_crop(page: Image.Image, row: int, field: str,
               transform: tuple[float, int] | None = None) -> Image.Image:
    scale, shift = transform if transform is not None else _row_transform(page)
    top, bottom = (round(v*scale+shift) for v in ROW_BOUNDS[row])
    left, right = PUNCH_COLUMNS[field]
    return page.crop((left + 7, top + 5, right - 7, bottom - 5))


def row_rect_original(image: Image.Image, row: int) -> tuple[int, int, int, int]:
    """Photo-space selection rectangle for mandatory manager review."""
    image = ImageOps.exif_transpose(image)
    left, top, right, bottom = _paper_box(image)
    scale, shift = _row_transform(normalized_page(image))
    y1, y2 = (round(v*scale+shift) for v in ROW_BOUNDS[row])
    return (round(left + 75 * (right-left) / PAGE_W),
            round(top + (y1 - 5) * (bottom-top) / PAGE_H),
            round(left + 546 * (right-left) / PAGE_W),
            round(top + (y2 + 5) * (bottom-top) / PAGE_H))


def _has_ink(cell: Image.Image) -> bool:
    """Detect faint pencil/pen by local contrast instead of absolute RGB darkness."""
    gray = np.asarray(cell.convert('L'))
    if min(gray.shape) < 8:
        return True
    background = cv2.GaussianBlur(gray, (21, 21), 0)
    inner = gray[:, 3:-3]
    contrast = background[:, 3:-3].astype('int16') - inner.astype('int16')
    mask = np.uint8((contrast > 13) & (inner < 230)) * 255
    _, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    connected = int(np.count_nonzero(stats[1:, cv2.CC_STAT_AREA] >= 3))
    return int(np.count_nonzero(mask)) >= 40 and connected >= 2


def _time_candidate(cell: Image.Image) -> str:
    """A proposed transcription, *not* automatically a clock punch."""
    from .ocr import _cleanup_time, _ocr_cell
    if not _has_ink(cell):
        return ''
    primary = _cleanup_time(_ocr_cell(cell, '0123456789:APMapm'))
    if re.fullmatch(r'(?:\d{1,2}:\d{2}|\d{3,4})(?:[AP])?', primary):
        return primary
    bw = ImageOps.autocontrast(ImageOps.grayscale(cell), cutoff=2)
    bw = ImageEnhance.Contrast(bw).enhance(2.3)
    bw = bw.resize((max(100, bw.width*4), max(48, bw.height*4)), Image.Resampling.LANCZOS)
    alternate = _cleanup_time(pytesseract.image_to_string(bw,
        config='--psm 13 -c tessedit_char_whitelist=0123456789:APMapm'))
    if re.fullmatch(r'(?:\d{1,2}:\d{2}|\d{3,4})(?:[AP])?', alternate):
        return alternate
    return primary or alternate


def scan_this_form(sheet, image: Image.Image) -> None:
    """Map the real paper's two time columns into in1/out1; require review."""
    from .core import DISPLAY, normalize_time
    from .ocr import _ocr_cell
    page = normalized_page(image)
    sheet.form_type = FORM_ID
    sheet.rotate_180_for_archive = False
    if not _header_matches(page) and _header_matches(page.rotate(180)):
        page = page.rotate(180)
        sheet.rotate_180_for_archive = True
    name = _ocr_cell(page.crop(NAME), 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
    name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name).strip()
    sheet.employee = name if len(name) >= 4 and len(name.split()) >= 2 else ''
    warnings = ["OCR suggestions require checking every punch against the original photograph.",
                "This form has no AM/PM field: a time like 6:00 needs manual AM/PM verification."]
    transform = _row_transform(page)
    for i in range(14):
        day = sheet.days[i]
        for field in ('in1', 'out1'):
            cell = field_crop(page, i, field, transform)
            if not _has_ink(cell):
                day.recognized[field] = ''
                continue
            suggestion = _time_candidate(cell)
            day.recognized[field] = suggestion
            canon, error = normalize_time(suggestion)
            explicit_24h = bool(re.fullmatch(r'(?:1[3-9]|2[0-3]):[0-5]\d', suggestion))
            explicit_ampm = bool(re.fullmatch(r'\d{1,2}:[0-5]\d[AP]', suggestion))
            if canon and not error and (explicit_ampm or explicit_24h):
                setattr(day, field, suggestion)
            else:
                warnings.append(
                    f"Week {i//7+1} {DISPLAY[i%7]}, {field}: "
                    f"writing visible; OCR suggestion {suggestion!r} needs verification"
                )
    sheet.scan_warnings = warnings
