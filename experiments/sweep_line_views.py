"""Offline image-view comparison. Inputs and reports stay outside the repo."""
import argparse
import json
import sys
from pathlib import Path
import math
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.offline_guard import block_network
block_network()

import cv2
import numpy as np
from PIL import Image, ImageOps
import onnxruntime as ort
ort.disable_telemetry_events()
from experiments.compare_line_ocr import clock_cells, prepare
from app.ocr import load_pages
from app.core import normalize_time


def view_of(cell, view):
    if view == 'raw':
        return prepare(cell, 'raw')
    result = prepare(cell, 'blue-tight')
    if view.startswith('rotate'):
        angle = float(view.removeprefix('rotate'))
        result = np.asarray(Image.fromarray(result).rotate(angle, expand=True, fillcolor='white'))
    elif view.startswith('width'):
        factor = float(view.removeprefix('width'))
        result = cv2.resize(result, (round(result.shape[1]*factor), result.shape[0]))
    elif view == 'thin':
        result = cv2.dilate(result, np.ones((2, 2), dtype='uint8'))
    elif view == 'thick':
        result = cv2.erode(result, np.ones((2, 2), dtype='uint8'))
    elif view == 'clean':
        ink = np.uint8(result[:, :, 0] < 128)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(ink)
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if area < 5 or (y < 3 and h < result.shape[0]*.2):
                result[labels == i] = 255
    return result


def infer(session, images, chars):
    output = []
    for start in range(0, len(images), 6):
        batch = images[start:start+6]
        width = max(320, max(math.ceil(48*a.shape[1]/a.shape[0]) for a in batch))
        tensor = np.zeros((len(batch), 3, 48, width), dtype='float32')
        for i, a in enumerate(batch):
            w = min(width, math.ceil(48*a.shape[1]/a.shape[0]))
            a = cv2.resize(a, (w, 48)).astype('float32')/127.5-1
            tensor[i, :, :, :w] = a.transpose(2, 0, 1)
        predictions = session.run(None, {'x': tensor})[0]
        for pred in predictions:
            indices = pred.argmax(axis=1)
            take = np.r_[True, indices[1:] != indices[:-1]] & (indices != 0)
            values = pred[np.arange(len(indices)), indices][take]
            text = ''.join(chars[i] for i in indices[take])
            output.append((text, float(values.mean()) if len(values) else 0,
                           float(values.min()) if len(values) else 0))
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--views', nargs='+', default=['raw', 'tight', 'clean',
        'rotate-5', 'rotate5', 'width0.75', 'width1.3', 'thin', 'thick'])
    a = p.parse_args()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(a.model, options, providers=['CPUExecutionProvider'])
    chars = ['blank'] + session.get_modelmeta().custom_metadata_map['character'].splitlines() + [' ']
    report = {'views': {}, 'model': Path(a.model).name}
    start = time.perf_counter()
    for page, image in enumerate(load_pages(a.input), 1):
        cells = clock_cells(image, True)
        for view in a.views:
            result = infer(session, [view_of(cell, view) for _, _, cell in cells], chars)
            entries = []
            for (row, field, _), (raw, score, minimum) in zip(cells, result):
                value, error = normalize_time(raw)
                entries.append(dict(page=page, row=row, field=field, raw=raw,
                    score=score, minimum=minimum, time=value if not error else ''))
            report['views'].setdefault(view, []).extend(entries)
            print(view, 'valid', [(e['row'], e['field'], e['raw'], round(e['minimum'], 3))
                  for e in entries if e['time']], flush=True)
    report['elapsed_seconds'] = round(time.perf_counter()-start, 3)
    Path(a.output).write_text(json.dumps(report, indent=2))
    print('saved', a.output, report['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
