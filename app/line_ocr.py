"""Local whole-entry OCR with conservative disagreement handling.

Confidence thresholds are development heuristics, not calibrated accuracy.
No reading approves a row or a sheet. No networking or automatic downloads.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from .core import display_time, normalize_time
from .model_assets import LINE_MODEL, LINE_MODEL_SHA256

VIEWS = ('raw', 'blue', 'clean', 'narrow')


class LineOCRError(RuntimeError):
    pass


@dataclass(frozen=True)
class Reading:
    text: str
    confidence: float
    minimum: float
    source: str


@dataclass(frozen=True)
class Decision:
    value: str
    raw: str
    status: str


def choose_time(readings: list[Reading]) -> Decision:
    """Abstain on plausible disagreements; never invent missing A/P suffixes."""
    groups = defaultdict(list)
    hints = set()
    for reading in readings:
        value, error = normalize_time(reading.text)
        if not value or error:
            continue
        digit = reading.source.startswith('digits-')
        plausible = (reading.minimum >= .60 if digit else
                     reading.confidence >= .80 and reading.minimum >= .40)
        if not plausible:
            continue
        hints.add(value)
        groups[value].append(reading)

    # A second plausible time is a review issue even when the first is stronger.
    raw = ' / '.join(dict.fromkeys(r.text.strip() for r in sorted(
        readings, key=lambda r: r.confidence, reverse=True) if r.text.strip()))[:100]
    if len(hints) > 1:
        return Decision('', raw, 'conflicting-readings')
    if not groups:
        return Decision('', raw, 'unreadable-or-missing-AM/PM')
    value, candidates = next(iter(groups.items()))
    line_sources = {r.source for r in candidates if not r.source.startswith('digits-')}
    strong = any((r.minimum >= .90 if r.source.startswith('digits-') else
                  r.confidence >= .97 and r.minimum >= .90) for r in candidates)
    if not strong and len(line_sources) < 2:
        return Decision('', raw, 'uncertain-reading')
    best = max(candidates, key=lambda r: r.confidence)
    return Decision(display_time(value), best.text.strip(), 'suggestion')


def prepare_view(image: Image.Image, view: str) -> np.ndarray:
    """Return a BGR view, keeping punctuation and the actual ink suffix."""
    import cv2
    if view not in VIEWS:
        raise ValueError('Unknown recognition view')
    rgb = np.asarray(image.convert('RGB'))
    if view == 'raw':
        return np.ascontiguousarray(rgb[:, :, ::-1])
    a = rgb.astype('int16')
    r, g, b = (a[:, :, i] for i in range(3))
    mask = (b-r > 19) & (b-g > 7) & (b < 248)
    if view == 'clean':
        # Remove only tiny disconnected specks, including small fragments that
        # cross a printed row boundary. Keep the main time and its colon dots.
        n, labels, stats, _ = cv2.connectedComponentsWithStats(np.uint8(mask))
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if area < 5 or (y < 3 and h < image.height*.20):
                mask[labels == i] = False
    if view in ('clean', 'narrow'):
        ys, xs = np.nonzero(mask)
        if len(xs):
            mask = mask[int(ys.min()):int(ys.max())+1, int(xs.min()):int(xs.max())+1]
    result = Image.fromarray(np.uint8(~mask)*255).convert('RGB')
    result = ImageOps.expand(result, border=5, fill='white')
    bgr = np.ascontiguousarray(np.asarray(result)[:, :, ::-1])
    if view == 'narrow':
        bgr = cv2.resize(bgr, (max(1, round(bgr.shape[1]*.75)), bgr.shape[0]))
    return bgr


def decode_ctc(probabilities: np.ndarray, characters: list[str], source: str) -> Reading:
    """Collapse repeated CTC labels, preserving repeats separated by blanks."""
    if probabilities.ndim != 2 or probabilities.shape[1] != len(characters):
        raise LineOCRError('Recognition dictionary does not match model output')
    labels = probabilities.argmax(axis=1)
    take = np.r_[True, labels[1:] != labels[:-1]] & (labels != 0)
    scores = probabilities[np.arange(len(labels)), labels][take]
    text = ''.join(characters[i] for i in labels[take])
    return Reading(text, float(scores.mean()) if len(scores) else 0.,
                   float(scores.min()) if len(scores) else 0., source)


class LineRecognizer:
    def __init__(self, model: Path = LINE_MODEL):
        model = Path(model)
        if not model.is_file():
            raise LineOCRError('Handwriting recognition model is missing')
        with model.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != LINE_MODEL_SHA256:
            raise LineOCRError('Handwriting recognition model failed integrity check')
        try:
            import onnxruntime as ort
            # Must precede creation of any session, including in the installer.
            ort.disable_telemetry_events()
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            self.session = ort.InferenceSession(str(model), options,
                                               providers=['CPUExecutionProvider'])
            metadata = self.session.get_modelmeta().custom_metadata_map
            self.characters = ['blank'] + metadata['character'].splitlines() + [' ']
            self.input_name = self.session.get_inputs()[0].name
        except Exception as exc:
            raise LineOCRError('Handwriting recognition engine could not start') from exc

    def recognize(self, images: list[Image.Image]) -> list[list[Reading]]:
        import cv2
        result = [[] for _ in images]
        for view in VIEWS:
            for start in range(0, len(images), 6):
                batch = [prepare_view(image, view) for image in images[start:start+6]]
                width = max(320, max(math.ceil(48*a.shape[1]/a.shape[0]) for a in batch))
                tensor = np.zeros((len(batch), 3, 48, width), dtype='float32')
                for i, a in enumerate(batch):
                    w = min(width, math.ceil(48*a.shape[1]/a.shape[0]))
                    resized = cv2.resize(a, (w, 48)).astype('float32')/127.5-1
                    tensor[i, :, :, :w] = resized.transpose(2, 0, 1)
                try:
                    predictions = self.session.run(None, {self.input_name: tensor})[0]
                except Exception as exc:
                    raise LineOCRError('Handwriting recognition could not read this page') from exc
                for i, prediction in enumerate(predictions):
                    result[start+i].append(decode_ctc(prediction, self.characters, view))
        return result


@lru_cache(maxsize=1)
def get_recognizer() -> LineRecognizer:
    return LineRecognizer()
