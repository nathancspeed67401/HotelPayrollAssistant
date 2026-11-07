"""Register the single-pair paper form using its printed headers and rules.

No employee handwriting supplies a row or clock-column boundary. A failed
registration returns None; callers must not populate guesses from fixed boxes.
"""
from __future__ import annotations
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image
from .form_geometry import FormGrid


def _header_rows(page: Image.Image) -> list[tuple[float,float]]:
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
    w, h = page.size
    header_bounds = _header_rows(page)
    if not header_bounds:
        return None
    headers = [v[0] for v in header_bounds]
    gray = np.asarray(page.convert('L'))
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY_INV, 41, 10)
    segments = cv2.HoughLinesP(binary, 1, np.pi/1800, threshold=65,
        minLineLength=round(w*.23), maxLineGap=round(w*.04))
    if segments is None:
        return None
    horizontal, vertical, edges = [], [], []
    midx, midy = w*.5, (headers[0]+headers[1])*.5
    for x1, y1, x2, y2 in segments[:, 0, :]:
        dx, dy = float(x2-x1), float(y2-y1)
        if abs(dx) > w*.45 and abs(dy) < abs(dx)*.07:
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
    # Text baselines and strike-throughs can form long Hough segments. A printed
    # rule must also be visible across both outer edges of the table.
    near = cv2.dilate(binary, np.ones((5,3),np.uint8))
    xs = np.linspace(left+5,right-5,400).astype(int)
    def support(line):
        a,b,_ = line
        ys = np.rint(a*xs+b).astype(int).clip(0,h-1)
        values = near[ys,xs] > 0
        return values.mean() > .64 and values[:60].mean() > .5 and values[-60:].mean() > .5
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
    positions = np.array([a*midx+b for a,b in rules])
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
                missing = 0
                cost = 0.
                for i in range(1,7):
                    expected = positions[start]+i*step
                    candidates = [j for j in range(start+1,end) if j > last
                                  and abs(positions[j]-expected) < step*.42]
                    if not candidates:
                        missing += 1
                        if missing > 1:
                            break
                        fraction = i/7
                        selected.append(tuple(rules[start][k]*(1-fraction)+rules[end][k]*fraction for k in range(2)))
                        cost += .6
                        continue
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
    grid = FormGrid(page.size, page.size, tuple(columns), tuple(body))
    for row in range(14):
        for col in range(2):
            if any(not (0 <= x < w and 0 <= y < h) for x,y in grid.cell_quad(row,col)):
                return None
    return grid
