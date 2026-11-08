"""Offline clock-specific second reader for unclear single-pair punches."""
from collections import defaultdict
from functools import lru_cache
import hashlib
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .core import display_time, normalize_time
from .line_ocr import Decision, LineOCRError, Reading, clock_key, decode_ctc, photo_clock_text

MODEL = Path(__file__).resolve().parent / 'assets' / 'clock_reader_v1.onnx'
MODEL_SHA256 = 'a6c19d350b488824b31366f3caf71a4994c7223cac20dde18d3d7c0c4bacb60f'
CHARACTERS = ['blank', *'0123456789:APM?']


def _clock_ink(image: Image.Image) -> np.ndarray:
    gray = np.asarray(image.convert('L'))
    height, width = gray.shape
    diameter = max(7, round(height * .26) | 1)
    paper = cv2.morphologyEx(gray, cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (diameter, diameter)))
    ink = np.uint8(cv2.subtract(paper, gray) > max(8, .07 * float(np.median(paper))))
    ink[:2, :] = ink[-2:, :] = 0
    ink[:, :2] = ink[:, -2:] = 0
    rules = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((1, max(9, round(width * .52))), np.uint8))
    rules[round(.15 * height):round(.85 * height)] = 0
    ink[rules > 0] = 0
    count, labels, stats, centers = cv2.connectedComponentsWithStats(ink)
    for i in range(1, count):
        if (stats[i, cv2.CC_STAT_AREA] < max(3, .06 * height)
                or (stats[i, cv2.CC_STAT_HEIGHT] < .13 * height
                    and not .16 * height < centers[i, 1] < .84 * height)):
            ink[labels == i] = 0
    ys, xs = np.nonzero(ink)
    if len(xs) >= 10:
        ink = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return 255 - ink * 255


class ClockRecognizer:
    def __init__(self, path: Path = MODEL):
        if not path.is_file():
            raise LineOCRError('Clock model is missing')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != MODEL_SHA256:
                raise LineOCRError('Clock model failed integrity check')
        try:
            import onnxruntime as ort
            ort.disable_telemetry_events()
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            self.session = ort.InferenceSession(str(path), options, providers=['CPUExecutionProvider'])
        except Exception as exc:
            raise LineOCRError('Clock model could not start') from exc

    def recognize(self, images: list[Image.Image]) -> list[list[Reading]]:
        inks = [_clock_ink(image) for image in images]
        readings: list[list[Reading]] = [[] for _ in inks]
        for height in (18, 23):
            tensor = np.zeros((len(inks), 1, 32, 160), np.float32)
            top = (32 - height) // 2
            for row, ink in enumerate(inks):
                width = min(152, max(1, round(height * ink.shape[1] / ink.shape[0])))
                pixels = cv2.resize(ink, (width, height)).astype(np.float32)
                tensor[row, 0, top:top + height, 4:4 + width] = 1 - pixels / 255
            try:
                predictions = self.session.run(None, {'pixels': tensor})[0]
            except Exception as exc:
                raise LineOCRError('Clock model could not read this page') from exc
            for scores, outputs in zip(predictions, readings, strict=True):
                reading = decode_ctc(scores, CHARACTERS, f'clock-{height}')
                outputs.append(Reading(photo_clock_text(reading.text), reading.confidence,
                                       reading.minimum, reading.source))
        return readings


@lru_cache(maxsize=1)
def get_clock_recognizer() -> ClockRecognizer:
    return ClockRecognizer()


def _literal(reading: Reading) -> tuple[str, bool]:
    return clock_key(reading.text), sum(ch.isdecimal() for ch in reading.text) >= 3


def review_transcription(readings: list[Reading]) -> Reading | None:
    """Keep a strongly agreed literal reading for review during an outage."""
    if len(readings) != 2:
        return None
    first, second = readings
    key = _literal(first)
    if (first.source == second.source or min(first.minimum, second.minimum) < .96
            or not key[0] or key != _literal(second)):
        return None
    return max(readings, key=lambda reading: reading.minimum)


def corroborate_clock(primary: list[Reading], secondary: list[Reading], original: Decision
                      ) -> tuple[Decision, Reading | None]:
    """Use independent weights to check the same ink. Only joint reads can be used."""
    if not primary or original.value:
        return original, None
    alternatives = defaultdict(list)
    for reading in secondary:
        key = _literal(reading)
        if key[0] and reading.confidence >= .80 and reading.minimum >= .40:
            alternatives[key].append(reading)
    if len(alternatives) != 1:
        return original, None
    (clock, minutes), matches = next(iter(alternatives.items()))
    best = max(matches, key=lambda reading: reading.minimum)
    if best.minimum < .65:
        return original, None
    direct = {_literal(reading) for reading in primary
              if reading.confidence >= .80 and reading.minimum >= .40 and clock_key(reading.text)}
    if any(other.rstrip('AP') != clock.rstrip('AP')
           or (other.endswith(('A', 'P')) and other[-1] != clock[-1]) for other, _ in direct):
        return original, None
    corroborated = (clock, minutes) in direct
    initial = max(primary, key=lambda reading: reading.confidence)
    # A very strong independent reading may help during manual review, but
    # lower-quality reads need support before replacing the original transcript.
    can_replace = corroborated or (not direct and best.minimum >= .90)
    preferred = best if can_replace and not clock_key(initial.text) else None
    hour = int(clock.split(':')[0])
    if corroborated and minutes and (clock.endswith(('A', 'P')) or hour == 0 or hour >= 13):
        value, error = normalize_time(clock)
        if value and not error:
            return Decision(display_time(value), best.text, 'suggestion'), preferred
    if preferred:
        return Decision('', best.text, 'uncertain-reading'), preferred
    return original, None
