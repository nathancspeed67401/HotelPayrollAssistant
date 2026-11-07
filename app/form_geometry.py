"""Locate this hotel's printed clock grid without using handwriting content."""
from __future__ import annotations
from dataclasses import dataclass
from PIL import Image

REF_W, REF_H = 958, 1350
ROW_Y = [(368 + 39*i, 405 + 39*i) for i in range(7)] + [(673 + 38*i, 712 + 38*i) for i in range(7)]
COL_X = ((215, 342), (350, 474), (479, 602), (612, 738))
_COLUMN_BORDERS = (213, 345, 478, 607, 745)


def _intersection(vertical, horizontal):
    a, b = vertical  # x = a*y + b
    c, d = horizontal  # y = c*x + d
    x = (a*d+b)/(1-a*c)
    return x, c*x+d


@dataclass(frozen=True)
class FormGrid:
    image_size: tuple[int, int]
    analysis_size: tuple[int, int]
    vertical: tuple
    row_bounds: tuple

    def cell_quad(self, row: int, column: int):
        sx = self.image_size[0]/self.analysis_size[0]
        sy = self.image_size[1]/self.analysis_size[1]
        top, bottom = self.row_bounds[row]
        left, right = self.vertical[column:column+2]
        return tuple((x*sx, y*sy) for x, y in (
            _intersection(left, top), _intersection(right, top),
            _intersection(right, bottom), _intersection(left, bottom)))

    def crop_cell(self, image: Image.Image, row: int, column: int) -> Image.Image:
        import cv2
        import numpy as np
        if image.size != self.image_size:
            raise ValueError('Grid belongs to a different image size')
        quad = np.asarray(self.cell_quad(row, column), dtype='float32')
        width = round((np.linalg.norm(quad[1]-quad[0]) + np.linalg.norm(quad[2]-quad[3]))/2)
        height = round((np.linalg.norm(quad[3]-quad[0]) + np.linalg.norm(quad[2]-quad[1]))/2)
        destination = np.asarray(((0, 0), (width-1, 0), (width-1, height-1),
                                  (0, height-1)), dtype='float32')
        matrix = cv2.getPerspectiveTransform(quad, destination)
        cell = cv2.warpPerspective(np.asarray(image.convert('RGB')), matrix,
                                  (width, height), borderValue=(255, 255, 255))
        inset = max(1, round(self.image_size[0]/REF_W))
        return Image.fromarray(cell).crop((inset, inset, width-inset, height-inset))


def find_form_grid(image: Image.Image) -> FormGrid | None:
    """Return a validated 14-row/four-clock-column grid, or abstain.

    Only long, neutral-colored printed rules contribute to alignment. Blue ink
    cannot supply a clock-column boundary. Partial or implausible grids fall
    back to the existing fixed crops rather than guessing another layout.
    """
    import cv2
    import numpy as np
    if image.width < 450 or image.height < 650:
        return None
    width = min(REF_W, image.width)
    height = round(image.height*width/image.width)
    if not 1.2 < height/width < 1.7:
        return None
    a = np.asarray(image.convert('RGB').resize((width, height))).astype('int16')
    mask = (a.max(axis=2)-a.min(axis=2) < 38) & (a.mean(axis=2) < 225)
    mask[:round(height*.22)] = False
    mask[round(height*.72):] = False
    segments = cv2.HoughLinesP(np.uint8(mask)*255, 1, np.pi/1800,
        threshold=65, minLineLength=round(height*.075), maxLineGap=round(width*.05))
    if segments is None:
        return None
    mid_y, mid_x = height*.5, width*.5
    vertical, horizontal = [], []
    for x1, y1, x2, y2 in segments[:, 0, :]:
        dx, dy = float(x2-x1), float(y2-y1)
        if abs(dy) > height*.09 and abs(dx) < abs(dy)*.08:
            slope = dx/dy
            vertical.append((slope, x1-slope*y1, abs(dy)))
        if abs(dx) > width*.35 and abs(dy) < abs(dx)*.06:
            slope = dy/dx
            horizontal.append((slope, y1-slope*x1, abs(dx)))
    selected = []
    for border in _COLUMN_BORDERS:
        expected = border*width/REF_W
        candidates = [v for v in vertical if abs(v[0]*mid_y+v[1]-expected) < width*.06]
        if not candidates:
            return None
        # Long rules are more reliable than short text/edge fragments.
        chosen = max(candidates, key=lambda line: line[2])
        selected.append(chosen[:2])
    slopes = np.asarray([v[0] for v in selected])
    if float(slopes.max()-slopes.min()) > .045:
        return None
    for y in (height*.3, height*.7):
        positions = [a*y+b for a, b in selected]
        gaps = np.diff(positions)
        if np.any(gaps < width*.10) or np.any(gaps > width*.19):
            return None

    # Merge the two edges of a printed rule and duplicate Hough segments.
    groups = []
    for line in sorted(horizontal, key=lambda h: h[0]*mid_x+h[1]):
        value = line[0]*mid_x+line[1]
        if groups and abs(value-groups[-1][0]) < 3:
            groups[-1][1].append(line)
            groups[-1][0] = float(np.average([h[0]*mid_x+h[1]
                for h in groups[-1][1]], weights=[h[2] for h in groups[-1][1]]))
        else:
            groups.append([value, [line]])
    rules = [max(group, key=lambda h: h[2])[:2] for _, group in groups]
    row_bounds = []
    for week in range(2):
        rows = ROW_Y[week*7:week*7+7]
        expected = [r[0]*height/REF_H for r in rows] + [rows[-1][1]*height/REF_H]
        step = (expected[-1]-expected[0])/7
        matched = []
        for value in expected:
            nearest = min(rules, key=lambda h: abs(h[0]*mid_x+h[1]-value), default=None)
            matched.append(nearest if nearest and abs(nearest[0]*mid_x+nearest[1]-value) < step*.34 else None)
        if sum(h is not None for h in matched) < 6 or matched[0] is None or matched[-1] is None:
            return None
        for i, rule in enumerate(matched):
            if rule is None:
                left = max(j for j in range(i) if matched[j] is not None)
                right = min(j for j in range(i+1, 8) if matched[j] is not None)
                fraction = (i-left)/(right-left)
                matched[i] = tuple(matched[left][k]*(1-fraction) + matched[right][k]*fraction
                                   for k in range(2))
        positions = [a*mid_x+b for a, b in matched]
        gaps = np.diff(positions)
        if np.any(gaps < step*.65) or np.any(gaps > step*1.35):
            return None
        row_bounds.extend(zip(matched[:-1], matched[1:]))
    grid = FormGrid(image.size, (width, height), tuple(selected), tuple(row_bounds))
    for row in range(14):
        for column in range(4):
            quad = grid.cell_quad(row, column)
            if any(not (0 <= x < image.width and 0 <= y < image.height) for x, y in quad):
                return None
    return grid
