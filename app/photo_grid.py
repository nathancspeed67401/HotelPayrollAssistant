"""Register the single-pair paper form using its printed headers and rules.

No employee handwriting supplies a row or clock-column boundary. A failed
registration returns None; callers must not populate guesses from fixed boxes.
"""
from __future__ import annotations
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps
from .form_geometry import FormGrid


def _header_rows(page: Image.Image) -> list[tuple[float, float, float | None]]:
    words = pytesseract.image_to_data(page, config='--psm 11',
                                     output_type=pytesseract.Output.DICT)
    labels = {'DATE','DAY','TIME','TIMEIN','TIMEOUT','IN','OUT','ROOMS','TOTAL',
              'HOUR','HOURS','ALOTTED','ALLOTTED','ALLOTED'}
    indices = [i for i,t in enumerate(words['text'])
               if re.sub('[^A-Z]','',t.upper()) in labels
               and page.width*.05 < words['left'][i] < page.width*.92
               and page.height*.16 < words['top'][i] < page.height*.75]
    groups = []
    for i in sorted(indices,key=lambda i:words['top'][i]):
        if groups and words['top'][i]-words['top'][groups[-1][-1]] < page.height*.045:
            groups[-1].append(i)
        else:
            groups.append([i])
    result = []
    for group in groups:
        texts = {re.sub('[^A-Z]','',words['text'][i].upper()) for i in group}
        if (len(group) < 3 and not texts.intersection({'TIMEIN','TIMEOUT','ROOMS'})) or not texts.intersection({'TIME','TIMEIN','TIMEOUT','OUT','ROOMS'}):
            continue
        first = min(words['top'][i] for i in group)
        baseline = [(words['left'][i],words['top'][i]) for i in group
                    if words['top'][i] < first+page.height*.014]
        slopes = [(y2-y1)/(x2-x1) for x1,y1 in baseline for x2,y2 in baseline
                  if x2-x1 > page.width*.15]
        slope = float(np.median(slopes)) if slopes else 0.
        top = float(np.median([y-slope*(x-page.width*.5) for x,y in baseline]))
        bottom = max(words['top'][i]+min(words['height'][i],24)
                     -slope*(words['left'][i]-page.width*.5) for i in group)
        saturdays = [words['top'][i]-slope*(words['left'][i]-page.width*.5)-4
                     for i,t in enumerate(words['text'])
                     if re.sub('[^A-Z]','',t.upper()) == 'SAT'
                     and words['left'][i] < page.width*.25
                     and first+10 < words['top'][i] < first+page.height*.12]
        result.append((top,bottom,min(saturdays) if saturdays else None))
    return result if len(result) == 2 and page.height*.20 < result[1][0]-result[0][0] < page.height*.36 else []


def find_photo_grid(page: Image.Image) -> FormGrid | None:
    header_bounds = _header_rows(page)
    gray = np.asarray(page.convert('L'))
    # A dim photo can suppress an otherwise visible rule at the first
    # threshold. Retry the printed evidence, never extrapolate a missing rule.
    for contrast in (10, 7, 5):
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY_INV, 41, contrast)
        grid = _grid_from_rules(page, binary, header_bounds)
        if grid is not None:
            return grid
    return None


def _grid_from_rules(page, binary, header_bounds):
    w, h = page.size
    segments = cv2.HoughLinesP(binary, 1, np.pi/1800, threshold=65,
        minLineLength=round(w*.23), maxLineGap=round(w*.04))
    if segments is None:
        return None
    horizontal, vertical, edges = [], [], []
    midx = w * .5
    midy = sum(bound[0] for bound in header_bounds) / 2 if header_bounds else h * .4
    for x1, y1, x2, y2 in segments[:, 0, :]:
        dx, dy = float(x2-x1), float(y2-y1)
        if abs(dx) > w*.23 and abs(dy) < abs(dx)*.07:
            a = dy/dx
            line = (a, y1-a*x1, abs(dx))
            if h*.15 < a*midx+line[1] < h*.85:
                horizontal.append(line)
                if abs(dx) > w*.70:
                    edges.append((min(x1,x2), max(x1,x2)))
        if abs(dy) > h*.22 and abs(dx) < abs(dy)*.07:
            a = dx/dy
            vertical.append((a, x1-a*y1, abs(dy)))
    if len(edges) < 6:
        return None
    left, right = np.median(edges, axis=0)
    table_width = right-left
    if not w*.65 < table_width < w*.97:
        return None
    columns = []
    for fraction in (.24, .39, .54):
        expected = left + table_width*fraction
        matches = [v for v in vertical if abs(v[0]*midy+v[1]-expected) < w*.035]
        if not matches:
            return None
        columns.append(max(matches, key=lambda v:v[2])[:2])
    gaps = np.diff([a*midy+b for a,b in columns])
    if np.any(gaps < w*.09) or np.any(gaps > w*.17):
        return None
    # A shadow may hide the totals side of a printed rule. In that case,
    # require continuous evidence across the date and both clock columns.
    near = cv2.dilate(binary, np.ones((5,3),np.uint8))
    xs = np.linspace(left+5,right-5,400).astype(int)
    def support(line):
        a,b,_ = line
        ys = np.rint(a*xs+b).astype(int).clip(0,h-1)
        values = near[ys,xs] > 0
        if values.mean() > .64 and values[:60].mean() > .5 and values[-60:].mean() > .5:
            return True
        right_a, right_b = columns[-1]
        clock_section = xs < right_a * ys + right_b + w * .02
        return values[:45].mean() > .68 and values[clock_section].mean() > .78
    horizontal = [line for line in horizontal if support(line)]
    # Combine both edges and duplicate segments of each printed horizontal rule.
    groups = []
    for line in sorted(horizontal, key=lambda v:v[0]*midx+v[1]):
        y = line[0]*midx+line[1]
        if groups and abs(y-groups[-1][0]) < h*.004:
            groups[-1][1].append(line)
        else:
            groups.append([y,[line]])
    rules = [max(g, key=lambda v:v[2])[:2] for _,g in groups]
    body = _fit_header_rows(rules, header_bounds, midx, h) if header_bounds else None
    if body is None or not _weekday_anchors_match(page, body, columns):
        body = _fit_short_headers(page, rules, left, right)
        if body is None or not _weekday_anchors_match(page, body, columns):
            body = _fit_tall_headers(page, rules, left, right, columns)
            if body is None:
                return None
    # Each clock separator needs visible printed support in both weeks. A
    # segment confined to one week cannot define the other week's columns.
    near_columns = cv2.dilate(binary, np.ones((3, 7), np.uint8))
    for top, bottom in ((body[0][0], body[6][1]), (body[7][0], body[-1][1])):
        for a, b in columns:
            ys = np.linspace(_line_y(top, a, b) + 4, _line_y(bottom, a, b) - 4, 100).astype(int)
            xs = np.rint(a * ys + b).astype(int)
            if np.any((xs < 0) | (xs >= w) | (ys < 0) | (ys >= h)):
                return None
            if np.mean(near_columns[ys, xs] != 0) < .55:
                return None
    grid = FormGrid(page.size, page.size, tuple(columns), tuple(body))
    for row in range(14):
        for col in range(2):
            quad = grid.cell_quad(row, col)
            if any(not (0 <= x < w and 0 <= y < h) for x, y in quad):
                return None
            tl, tr, br, bl = quad
            if not all(w * .07 < width < w * .19 for width in (tr[0] - tl[0], br[0] - bl[0])):
                return None
            if not all(h * .018 < height < h * .065 for height in (bl[1] - tl[1], br[1] - tr[1])):
                return None
    return grid


def _line_y(horizontal, a, b):
    slope, offset = horizontal
    return (slope * b + offset) / (1 - slope * a)


_WEEKDAYS = {
    'SAT': 0, 'SUN': 1, 'MON': 2, 'TUE': 3, 'TUES': 3, 'WED': 4,
    'THU': 5, 'THUR': 5, 'THURS': 5, 'FRI': 6,
}


def _weekday_anchors_match(page, body, columns):
    """Check the day order against printed text outside the punch columns."""
    result = _read_weekday_anchors(page, body, columns, 1.87, 1.03)
    if result is not None:
        return result
    # Retry toward the clock divider when the first crop has too few weekday
    # matches. A conflicting weekday always rejects the grid.
    return _read_weekday_anchors(page, body, columns, 1.60, .75) is True


def _read_weekday_anchors(page, body, columns, left_gap, right_gap) -> bool | None:
    """Return True for matched rows, False for a conflict, or None if unclear."""
    w, h = page.size
    a, b = columns[0]
    next_a, next_b = columns[1]
    pitch = (next_a - a) * h * .5 + next_b - b
    # The weekday text is in the first printed column, two columns before
    # the clocks. This search band includes the margin beside the date rule.
    band_left = (a, max(b - left_gap * pitch, 1 + abs(a) * h))
    band_right = (a, b - right_gap * pitch)
    if band_right[1] - band_left[1] < w * .06:
        return None
    band = FormGrid(page.size, page.size, (band_left, band_right), tuple(body))
    row_height = 75
    strip = Image.new('L', (round(pitch * 2), row_height * 14), 255)
    for row in range(14):
        crop = band.crop_cell(page, row, 0).convert('L')
        dark = 255 - np.asarray(crop)
        vertical = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((round(crop.height * .68), 1), np.uint8))
        horizontal = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((1, round(crop.width * .50)), np.uint8))
        text = 255 - cv2.subtract(dark, np.maximum(vertical, horizontal))
        crop = ImageOps.autocontrast(Image.fromarray(text), cutoff=1)
        size = (min(strip.width, round(crop.width * (row_height - 8) / crop.height)), row_height - 8)
        crop = crop.resize(size, Image.Resampling.BICUBIC)
        strip.paste(crop, (0, row * row_height + 4))
    anchors = [set(), set()]
    smooth = Image.fromarray(cv2.GaussianBlur(np.asarray(strip), (5, 5), 0))
    for view, mode in ((strip, 6), (strip, 11), (smooth, 11)):
        words = pytesseract.image_to_data(view, config=f'--psm {mode}', output_type=pytesseract.Output.DICT)
        for word, top, height in zip(words['text'], words['top'], words['height']):
            weekday = _WEEKDAYS.get(re.sub('[^A-Z]', '', word.upper()))
            if weekday is None:
                continue
            row = (top + height // 2) // row_height
            if row >= 14 or weekday != row % 7:
                return False
            anchors[row // 7].add(weekday)
        if all(len(days) >= 2 and max(days) - min(days) >= 2 for days in anchors):
            return True
    # One printed weekday in each week pins the row order. Require a
    # second, separated anchor somewhere on a sheet with weak weekday print.
    if all(anchors) and any(max(days) - min(days) >= 2 for days in anchors):
        return True
    return None


def _fit_header_rows(rules, header_bounds, midx, h):
    positions = np.array([a*midx+b for a,b in rules])
    headers = [bound[0] for bound in header_bounds]
    body = []
    for week, header in enumerate(headers):
        if week == 0:
            # The next header is printed immediately below the last Friday rule.
            ends = np.where((positions > headers[1]-h*.018) & (positions < headers[1]+h*.002))[0]
            starts = np.where((positions >= header_bounds[week][1]-12) & (positions < header_bounds[week][1]+h*.035))[0]
        else:
            starts = np.where((positions >= header_bounds[week][1]-12) & (positions < header_bounds[week][1]+h*.035))[0]
            ends = np.where((positions > header+h*.19) & (positions < header+h*.29))[0]
        # Printed SAT anchors the first daily row. Header text itself can form
        # a Hough segment; the Saturday label prevents a smooth one-day shift.
        saturday = header_bounds[week][2]
        if saturday is not None:
            starts = np.where((positions > header+h*.006) & (positions < header+h*.10))[0]
            starts = sorted(starts,key=lambda j:abs(positions[j]-saturday))[:1]
            if starts and abs(positions[starts[0]]-saturday) > h*.018:
                return None
        elif len(starts):
            starts = starts[:1]
        best = None
        for start in starts:
            for end in ends:
                step = (positions[end]-positions[start])/7
                if not h*.025 < step < h*.045:
                    continue
                selected = [rules[start]]
                last = start
                cost = 0.
                for i in range(1,7):
                    expected = positions[start]+i*step
                    candidates = [j for j in range(start+1,end) if j > last
                                  and abs(positions[j]-expected) < step*.42]
                    if not candidates:
                        break
                    j = min(candidates,key=lambda j:abs(positions[j]-expected))
                    selected.append(rules[j])
                    last = j
                    cost += abs(positions[j]-expected)/step
                if len(selected) != 7:
                    continue
                selected.append(rules[end])
                deltas = np.diff([a*midx+b for a,b in selected])/step
                if np.any(deltas < .60) or np.any(deltas > 1.45):
                    continue
                # Prefer a complete grid with the earliest body start. This
                # excludes the weekly total line after Friday on week two.
                score = cost + (positions[start]-header)/h*4
                if best is None or score < best[0]:
                    best = score, selected
        if best is None:
            return None
        selected = best[1]
        body.extend(zip(selected[:-1],selected[1:]))
    return body


def _fit_short_headers(page, rules, left, right):
    """Recover two weeks from observed rules and individually rectified headers."""
    w, h = page.size
    gaps = np.diff([slope * w * .5 + offset for slope, offset in rules])
    candidates = []
    for start in range(len(rules) - 16):
        # Each narrow header must be followed by all eight day boundaries.
        # The first Friday's bottom rule is also the second header's top.
        for header in (start, start + 8):
            daily_gaps = gaps[header + 1:header + 8]
            step = np.median(daily_gaps)
            if not (h * .025 < step < h * .045 and .28 * step < gaps[header] < .72 * step
                    and np.all((daily_gaps > .75 * step) & (daily_gaps < 1.30 * step))):
                break
        else:
            candidates.append(start)
    if len(candidates) != 1:
        return None
    start = candidates[0]
    headers = ((rules[start], rules[start + 1]), (rules[start + 8], rules[start + 9]))
    if not _headers_match(page, headers, left, right):
        return None
    return [(rules[index], rules[index + 1])
            for header in (start, start + 8) for index in range(header + 1, header + 8)]


def _fit_tall_headers(page, rules, left, right, columns):
    """Recover taller, locally readable headers above two observed weeks."""
    w, h = page.size
    positions = np.array([a * w * .5 + b for a, b in rules])
    weeks = []
    for start in range(1, len(rules) - 7):
        gaps = np.diff(positions[start:start + 8])
        step = np.median(gaps)
        if h * .025 < step < h * .045 and np.all((gaps > .72 * step) & (gaps < 1.50 * step)):
            weeks.append((start, step))
    matched = None
    for first, first_step in weeks:
        friday_end = first + 7
        for second, second_step in weeks:
            if second <= friday_end:
                continue
            second_height = positions[second] - positions[friday_end]
            if not .25 * second_step < second_height < 1.65 * second_step:
                continue
            body = [(rules[i], rules[i + 1]) for start in (first, second) for i in range(start, start + 7)]
            for header in range(first - 1, -1, -1):
                first_height = positions[first] - positions[header]
                if first_height >= 1.65 * first_step:
                    break
                if not .25 * first_step < first_height or not .6 < first_height / second_height < 1.65:
                    continue
                if first_height < .72 * first_step and second_height < .72 * second_step:
                    continue  # Already handled by the short-header matcher.
                headers = ((rules[header], rules[first]), (rules[friday_end], rules[second]))
                if (_headers_match(page, headers, left, right)
                        and _weekday_anchors_match(page, body, columns)):
                    if matched is not None and matched != body:
                        return None
                    matched = body
                    break
    return matched


def _headers_match(page, headers, left, right):
    header_grid = FormGrid(page.size, page.size, ((0, left + 3), (0, right - 3)), headers)
    clock_labels = {'TIME', 'TIMEIN', 'TIMEOUT', 'IN', 'OUT'}
    other_labels = {'DATE', 'DAY', 'ROOMS', 'ALOTTED', 'ALLOTED', 'ALLOTTED', 'TOTAL', 'HOUR', 'HOURS'}
    directional_labels = {'TIMEIN', 'TIMEOUT', 'IN', 'OUT'}
    labels_by_header = []
    for row in range(2):
        gray = ImageOps.autocontrast(header_grid.crop_cell(page, row, 0).convert('L'), cutoff=1)
        binary = cv2.adaptiveThreshold(np.asarray(gray), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 25, 8)
        labels = set()
        for view, mode in ((gray, 11), (Image.fromarray(binary), 11), (Image.fromarray(binary), 7)):
            if mode == 7 and labels & clock_labels and labels & other_labels:
                break
            enlarged = view.resize((2 * view.width, 2 * view.height), Image.Resampling.BICUBIC)
            text = pytesseract.image_to_string(ImageOps.expand(enlarged, border=12, fill=255),
                                               config=f'--psm {mode}')
            labels.update(re.findall(r'[A-Z]+', text.upper()))
        if not labels & clock_labels or not labels & other_labels:
            return False
        labels_by_header.append(labels)
    return bool(set.union(*labels_by_header) & directional_labels)
