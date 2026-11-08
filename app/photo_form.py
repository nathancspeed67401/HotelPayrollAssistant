"""Photo-form OCR for the hotel's actual single-pair Comfort Suites paper sheet.

Camera alignment and reading suggestions are experimental. No AM/PM is guessed.
Never distribute private employee timesheet photographs with the repository.
"""
from __future__ import annotations
from dataclasses import replace
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


def _portrait(image: Image.Image) -> tuple[Image.Image, int]:
    image = ImageOps.exif_transpose(image).convert('RGB')
    if image.width > image.height:
        return image.rotate(90, expand=True), 90
    return image, 0


def normalized_page(image: Image.Image) -> Image.Image:
    portrait, _ = _portrait(image)
    return portrait.crop(_paper_box(portrait)).resize((PAGE_W, PAGE_H), Image.Resampling.LANCZOS)


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
    # Registered cells can retain both edges of a printed border after camera
    # resampling. Ignore only the perimeter; interior strike-throughs remain
    # visible writing requiring explicit manager disposition.
    if min(gray.shape) > 18:
        gray = gray[5:-5,5:-5]
    background = cv2.GaussianBlur(gray, (21, 21), 0)
    inner = gray[:, 3:-3]
    paper = background[:, 3:-3].astype('int16')
    contrast = paper - inner
    # A dark photo compresses the difference between paper and pencil.
    # Lower the contrast threshold there while keeping a floor for noise.
    threshold = np.clip(.075 * paper, 8, 13)
    mask = np.uint8((contrast > threshold) & (inner < 230)) * 255
    _, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    connected = int(np.count_nonzero(stats[1:, cv2.CC_STAT_AREA] >= 3))
    return int(np.count_nonzero(mask)) >= 25 and (connected >= 2 or bool(np.any(stats[1:, cv2.CC_STAT_AREA] >= 20)))


def _has_faint_ink(cell: Image.Image) -> bool:
    """Find coherent low-contrast strokes in an otherwise blank-looking cell."""
    gray = np.asarray(cell.convert('L'))
    if min(gray.shape) < 24:
        return False
    gray = gray[5:-5, 8:-8]
    height, width = gray.shape
    paper = cv2.GaussianBlur(gray, (21, 21), 0).astype('int16')
    contrast = paper - gray
    mask = np.uint8((contrast >= 4) & (contrast <= 18))
    _, _, stats, centers = cv2.connectedComponentsWithStats(mask)
    strokes = []
    for index, (x, y, w, h, area) in enumerate(stats[1:], 1):
        if (x == 0 or y == 0 or x + w >= width or y + h >= height or w < 2
                or h < .25 * height or w > .32 * width
                or area < max(6, .26 * height) or area > .80 * w * h):
            continue
        strokes.append((x, x + w, centers[index, 1]))
    if len(strokes) < 2:
        return False
    left = min(x1 for x1, _, _ in strokes)
    right = max(x2 for _, x2, _ in strokes)
    rows = [y for _, _, y in strokes]
    return right - left >= .13 * width and max(rows) - min(rows) <= .34 * height


def _hue_distance(hues: np.ndarray, center: int) -> np.ndarray:
    return np.abs((hues - center + 90) % 180 - 90)


def _has_overlapping_ink_colors(cell: Image.Image) -> bool:
    """Find distinct pen colors sharing the same stroke area."""
    width = round(cell.width * 48 / cell.height)
    rgb = np.asarray(cell.convert('RGB').resize((width, 48), Image.Resampling.BILINEAR))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    contrast = cv2.GaussianBlur(gray, (21, 21), 0).astype('int16') - gray
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0].astype('int16')
    colored = (hsv[:, :, 1] >= 52) & (contrast >= 18)
    colored[:5] = colored[-5:] = False
    colored[:, :8] = colored[:, -8:] = False
    histogram = np.bincount(hue[colored], minlength=180)
    weights = sum(np.roll(histogram, shift) for shift in range(-9, 10))
    primary = int(weights.argmax())
    weights[_hue_distance(np.arange(180), primary) < 38] = 0
    secondary = int(weights.argmax())
    if weights[secondary] < 12:
        return False

    first = colored & (_hue_distance(hue, primary) <= 10)
    second = colored & (_hue_distance(hue, secondary) <= 10)
    first_y, first_x = np.nonzero(first)
    second_y, second_x = np.nonzero(second)
    if (min(first_x.max(), second_x.max()) - max(first_x.min(), second_x.min()) < 5
            or min(first_y.max(), second_y.max()) - max(first_y.min(), second_y.min()) < 5):
        return False

    # Nearby strokes of both colors distinguish an overwrite from a pen
    # change between separate parts of an otherwise readable clock.
    neighborhood = np.ones((5, 5), np.uint8)
    near_first = cv2.dilate(first.astype(np.uint8), neighborhood) > 0
    near_second = cv2.dilate(second.astype(np.uint8), neighborhood) > 0
    return min(np.count_nonzero(first & near_second), np.count_nonzero(second & near_first)) >= 9


def _has_stacked_ink(cell: Image.Image) -> bool:
    """Find two broad, vertically separated ink bands in the same clock cell."""
    width = round(48 * cell.width / cell.height)
    gray = np.asarray(cell.convert('L').resize((width, 48), Image.Resampling.BILINEAR))
    paper = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    ink = cv2.subtract(paper, gray) >= max(12, .08 * float(np.median(paper)))
    ink[:4] = ink[-4:] = False
    ink[:, :8] = ink[:, -8:] = False
    rows = np.flatnonzero(ink.sum(axis=1) >= 3)
    bands = []
    for group in np.split(rows, np.flatnonzero(np.diff(rows) > 1) + 1):
        if len(group) < 6:
            continue
        columns = np.flatnonzero(ink[group].any(axis=0))
        if columns[-1] - columns[0] >= .22 * width and np.count_nonzero(ink[group]) >= 40:
            bands.append((group, columns))
    if len(bands) != 2:
        return False
    (top, top_columns), (bottom, bottom_columns) = bands
    gap = bottom[0] - top[-1] - 1
    overlap = min(top_columns[-1], bottom_columns[-1]) - max(top_columns[0], bottom_columns[0])
    return 2 <= gap <= 9 and overlap >= .18 * width and len(top) + len(bottom) >= 15


def _has_strike_through(cell: Image.Image) -> bool:
    """Find a long stroke through the writing before offering a suggestion."""
    height = 48
    width = round(height * cell.width / cell.height)
    gray = cv2.resize(np.asarray(cell.convert('L')), (width, height), interpolation=cv2.INTER_AREA)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    paper = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    ink = cv2.subtract(paper, gray) > max(9, .06 * float(np.median(paper)))
    lines = cv2.HoughLinesP(np.uint8(ink) * 255, 1, np.pi / 180,
                            threshold=round(.39 * width), minLineLength=round(.69 * width),
                            maxLineGap=max(2, round(.035 * width)))

    # Registration can leave a faint printed rule at either row edge.
    # Require supporting ink in the interior of the cell.
    top, bottom = round(.12 * height), round(.86 * height)
    left, right = round(.18 * width), round(.82 * width)
    y, x = np.nonzero(ink[top:bottom, left:right])
    y += top
    x += left
    for x1, y1, x2, y2 in (() if lines is None else lines[:, 0]):
        if abs(x2 - x1) < .68 * width or abs(y2 - y1) > .75 * height:
            continue
        slope = (y2 - y1) / (x2 - x1)
        center = y1 + slope * (width / 2 - x1)
        if not .20 * height < center < .80 * height:
            continue
        distance = y - (y1 + slope * (x - x1))
        above = (-.42 * height < distance) & (distance < -3)
        below = (3 < distance) & (distance < .42 * height)
        # Require ink on both sides of the stroke. A printed rule or an
        # underline below the time cannot supply this evidence on its own.
        if (np.count_nonzero(above) >= 14 and np.count_nonzero(below) >= 14
                and np.ptp(x[above]) >= .18 * width and np.ptp(x[below]) >= .18 * width):
            return True
    return _bridges_handwritten_ink(ink, x, y)


def _bridges_handwritten_ink(ink: np.ndarray, x: np.ndarray, y: np.ndarray) -> bool:
    """Require a short stroke to cross separate ink groups and bridge a gap."""
    height, width = ink.shape
    lines = cv2.HoughLinesP(np.uint8(ink) * 255, 1, np.pi / 180,
                            threshold=round(.34 * width), minLineLength=round(.47 * width),
                            maxLineGap=max(2, round(.035 * width)))
    if lines is None:
        return False
    line_ink = cv2.dilate(np.uint8(ink), np.ones((3, 1), dtype=np.uint8))
    for x1, y1, x2, y2 in lines[:, 0]:
        if abs(x2 - x1) < .47 * width or abs(y2 - y1) > .75 * height:
            continue
        slope = (y2 - y1) / (x2 - x1)
        midpoint = y1 + slope * (width * .5 - x1)
        if not .20 * height < midpoint < .80 * height:
            continue
        cols = np.arange(min(x1, x2), max(x1, x2) + 1)
        rows = np.rint(y1 + slope * (cols - x1)).astype(int)
        coverage = np.mean(line_ink[rows, cols])
        if coverage < .90:
            continue

        distance = y - (y1 + slope * (x - x1))
        above = (-20 < distance) & (distance < -3)
        below = (3 < distance) & (distance < 20)
        if (np.count_nonzero(above) < 14 or np.count_nonzero(below) < 14
                or np.ptp(x[above]) < .18 * width or np.ptp(x[below]) < .18 * width):
            continue
        start, end = np.percentile(x[above | below], (10, 90))
        overlap = min(cols[-1], end) - max(cols[0], start)
        if overlap < .80 * (end - start):
            continue

        upper = np.bincount(x[(-10 < distance) & (distance < -3)], minlength=width) > 0
        lower = np.bincount(x[(3 < distance) & (distance < 10)], minlength=width) > 0
        crossings = (upper & lower)[cols]
        starts = np.flatnonzero(crossings & ~np.r_[False, crossings[:-1]])
        ends = np.flatnonzero(crossings & ~np.r_[crossings[1:], False])
        substantial = ends > starts
        starts, ends = starts[substantial], ends[substantial]
        if len(starts) < 2 or starts[-1] - ends[0] < .16 * width:
            continue
        # Along a true cancellation the stroke continues through paper
        # between the crossed glyphs. An elongated digit alone cannot do that.
        interval = cols[ends[0]:starts[-1] + 1]
        gap = (~upper & ~lower)[interval]
        if np.any(gap[:-2] & gap[1:-1] & gap[2:]):
            return True
        # Dense writing can close the gap on one side of a cancellation.
        # Require a continuous horizontal stroke through at least four
        # crossings, plus a visible tail beyond the outer crossings.
        tail = max(starts[0], len(cols) - 1 - ends[-1])
        if len(starts) < 4 or abs(y2 - y1) > 4 or coverage < .98 or tail < .07 * width:
            continue
        for clear in (~upper[interval], ~lower[interval]):
            if np.any(clear[:-2] & clear[1:-1] & clear[2:]):
                return True
    return False


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


def scan_this_form(sheet, image: Image.Image) -> bool:
    """Try the single-pair reader; every recognized clock remains a proposal."""
    from .core import DISPLAY
    from .ocr import _ocr_cell
    from .line_ocr import PHOTO_VIEWS, LineOCRError, choose_clock, get_recognizer, photo_clock_text
    from .photo_grid import find_photo_grid, find_shadowed_photo_grid
    upright, rotation = _portrait(image)
    left, paper_top, right, paper_bottom = _paper_box(upright)
    paper = upright.crop((left, paper_top, right, paper_bottom))
    page = paper.resize((PAGE_W, PAGE_H), Image.Resampling.LANCZOS)
    flipped_page = None if _header_matches(page) else page.rotate(180)
    flip = flipped_page is not None and _header_matches(flipped_page)
    grid = find_photo_grid(flipped_page if flip else page)
    if flipped_page is not None and not flip and grid is None:
        # The table can identify the form even when the page heading is
        # unreadable. Only a verified table can select this orientation.
        grid = find_photo_grid(flipped_page)
        if grid is None:
            return False
        flip = True
    if grid is None:
        # The header established the form and orientation. Flatten shadows
        # only for printed registration. OCR still sees the original pixels.
        grid = find_shadowed_photo_grid(flipped_page if flip else page)
    if flip:
        paper = paper.rotate(180)
        page = flipped_page
        rotation = (rotation + 180) % 360
        left, right = upright.width - right, upright.width - left
        paper_top, paper_bottom = upright.height - paper_bottom, upright.height - paper_top
    sheet.form_type = FORM_ID
    sheet.archive_rotation = rotation
    sheet.rotate_180_for_archive = rotation == 180
    warnings = ["OCR suggestions require checking every punch against the original photograph.",
                "Use a suggested time only after comparing it with the photograph."]
    if grid is None:
        warnings.append('Printed rows could not be registered. No times were populated. Read the full photograph.')
        for day in sheet.days:
            for field in PUNCH_COLUMNS:
                day.observations[field] = {'status':'alignment-failed','raw':''}
        sheet.scan_warnings = warnings
        return True
    # Derive the employee area from the actual registered columns and first row.
    x = grid.cell_quad(0,0)[0][0]
    top = grid.cell_quad(0,0)[0][1]
    name = _ocr_cell(page.crop((max(0,x-200),max(0,top-110),x+120,max(0,top-30))),
                     'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
    name = re.sub(r'(?<=[a-z])(?=[A-Z])',' ',name).strip()
    sheet.employee = name if len(name) >= 4 and len(name.split()) >= 2 else ''
    source_grid = replace(grid, image_size=paper.size)
    sheet.review_boxes = []
    cells = []
    for row in range(14):
        quad = grid.cell_quad(row,0)+grid.cell_quad(row,1)
        x1,x2 = min(x for x,y in quad)-140,max(x for x,y in quad)+8
        y1,y2 = min(y for x,y in quad)-4,max(y for x,y in quad)+4
        sheet.review_boxes.append([
            round(left+max(0,x1)*(right-left)/PAGE_W),
            round(paper_top+max(0,y1)*(paper_bottom-paper_top)/PAGE_H),
            round(left+min(PAGE_W,x2)*(right-left)/PAGE_W),
            round(paper_top+min(PAGE_H,y2)*(paper_bottom-paper_top)/PAGE_H)])
        for col,field in enumerate(PUNCH_COLUMNS):
            cell = source_grid.crop_cell(paper, row, col)
            # The ink gate's thresholds are in normalized pixels. Send the
            # native rectified crop to the reader so it keeps faint strokes.
            ink_view = cell.resize(grid.crop_size(row, col), Image.Resampling.LANCZOS)
            if not _has_ink(ink_view):
                sheet.days[row].recognized[field] = ''
                status = 'possible-faint-ink' if _has_faint_ink(ink_view) else 'blank'
                sheet.days[row].observations[field] = {'status':status,'raw':''}
                if status == 'possible-faint-ink':
                    warnings.append(f'Week {row//7+1} {DISPLAY[row%7]}, {field}: check faint writing')
            else:
                cells.append((row,field,cell))
    readings = [[] for _ in cells]
    primary_failed = False
    if cells:
        try:
            readings = get_recognizer().recognize([cell for _,_,cell in cells],views=PHOTO_VIEWS)
        except LineOCRError as exc:
            primary_failed = True
            warnings.append(f'{exc}. Any alternate reading is for review only. Enter punches from the photograph.')
    readings = [[replace(reading, text=photo_clock_text(reading.text)) for reading in candidates]
                for candidates in readings]
    decisions = [choose_clock(candidates) for candidates in readings]
    second_pass = [i for i, decision in enumerate(decisions)
                   if primary_failed or (readings[i] and not decision.value)]
    preferred = {}
    if second_pass:
        from .clock_ocr import corroborate_clock, get_clock_recognizer, review_transcription
        try:
            extra = get_clock_recognizer().recognize([cells[i][2] for i in second_pass])
        except LineOCRError as exc:
            warnings.append(str(exc) + '. Verify unclear writing from the photograph.')
        else:
            for i, secondary in zip(second_pass, extra):
                if primary_failed:
                    transcript = review_transcription(secondary)
                    if transcript and not _has_strike_through(cells[i][2]):
                        decisions[i] = replace(decisions[i], raw=transcript.text, status='alternate-reader-review')
                        preferred[i] = transcript
                else:
                    decisions[i], preferred[i] = corroborate_clock(readings[i], secondary, decisions[i])
    for i, ((row,field,cell), candidates, decision) in enumerate(zip(cells,readings,decisions)):
        if decision.value and _has_strike_through(cell):
            decision = replace(decision, value='', status='possible-strike-through')
        if decision.value and _has_overlapping_ink_colors(cell):
            decision = replace(decision, value='', status='possible-overwrite')
        if decision.value and _has_stacked_ink(cell):
            decision = replace(decision, value='', status='possible-stacked-writing')
        day = sheet.days[row]
        day.recognized[field] = decision.raw
        day.observations[field] = {
            'status':decision.status,'raw':decision.raw,'proposal':decision.value,
            'candidates':[{'text':r.text,'confidence':r.confidence,'minimum':r.minimum,'source':r.source}
                          for r in candidates],
            'confidence_is_calibrated':False}
        if transcript := preferred.get(i):
            day.observations[field]['transcription'] = {'text': transcript.text,
                                                        'confidence': transcript.confidence}
        if decision.value:
            warnings.append(f'Week {row//7+1} {DISPLAY[row%7]}, {field}: compare the suggested time with the photograph')
        else:
            warnings.append(f"Week {row//7+1} {DISPLAY[row%7]}, {field}: writing needs review "
                            f"— {decision.status} (read: {decision.raw[:60]})")
    sheet.scan_warnings = warnings
    return True
