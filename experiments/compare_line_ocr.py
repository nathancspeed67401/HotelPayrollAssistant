"""Reproducible local line-recognition experiment; does not alter payroll data.

Input images and output predictions may contain payroll information. Keep them
outside the source repository. Download public weights separately: recognition
is performed with telemetry disabled and outbound network syscalls denied.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core import TIME_FIELDS, normalize_time
from app.ocr import COL_X, ROW_Y, _crop_scaled, load_pages
from app.form_geometry import find_form_grid


def clock_cells(image: Image.Image, registered=False):
    cells = []
    grid = find_form_grid(image) if registered else None
    if registered and grid is None:
        raise ValueError('Printed grid could not be reliably aligned')
    for row, (top, bottom) in enumerate(ROW_Y):
        for column, (field, (left, right)) in enumerate(zip(TIME_FIELDS, COL_X)):
            cells.append((row, field, grid.crop_cell(image, row, column) if grid else
                _crop_scaled(image, (left, top + 3, right, bottom - 3))))
    return cells


def prepare(image: Image.Image, view: str) -> np.ndarray:
    if view == 'raw':
        result = image.convert('RGB')
    else:
        a = np.asarray(image.convert('RGB')).astype('int16')
        red, green, blue = (a[:, :, i] for i in range(3))
        mask = (blue-red > 19) & (blue-green > 7) & (blue < 248)
        result = Image.fromarray(np.uint8(~mask) * 255).convert('RGB')
        if view == 'blue-tight':
            ys, xs = np.nonzero(mask)
            if len(xs):
                result = result.crop((int(xs.min()), int(ys.min()),
                    int(xs.max()) + 1, int(ys.max()) + 1))
        result = ImageOps.expand(result, border=5, fill='white')
    return cv2.cvtColor(np.asarray(result), cv2.COLOR_RGB2BGR)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--model', choices=('v5-english', 'v6-small', 'v6-medium'),
                        default='v6-small')
    parser.add_argument('--model-root')
    parser.add_argument('--registered', action='store_true')
    parser.add_argument('--views', nargs='+', default=['raw', 'blue', 'blue-tight'],
                        choices=('raw', 'blue', 'blue-tight'))
    args = parser.parse_args()

    from experiments.offline_guard import block_network
    block_network()
    import onnxruntime
    onnxruntime.disable_telemetry_events()
    from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    params = {'Global.use_det': False, 'Global.use_cls': False,
              'Global.log_level': 'warning', 'Rec.lang_type': LangRec.EN,
              'Rec.ocr_version': OCRVersion.PPOCRV5 if args.model == 'v5-english' else OCRVersion.PPOCRV6,
              'Rec.model_type': ModelType.MOBILE if args.model == 'v5-english' else
                  (ModelType.MEDIUM if args.model == 'v6-medium' else ModelType.SMALL),
              'EngineConfig.onnxruntime.intra_op_num_threads': 2,
              'EngineConfig.onnxruntime.inter_op_num_threads': 1}
    if args.model_root:
        params['Global.model_root_dir'] = args.model_root
    engine = RapidOCR(params=params)
    recognizer = engine._load_rec_model()
    report = {'input': str(Path(args.input).resolve()), 'model': args.model,
              'views': {}, 'registered': args.registered,
              'purpose': 'development experiment; no independent accuracy claim'}
    started = time.perf_counter()
    for page, image in enumerate(load_pages(args.input), 1):
        cells = clock_cells(image, args.registered)
        for view in args.views:
            result = recognizer(TextRecInput(img=[prepare(cell, view) for _, _, cell in cells]))
            entries = []
            for (row, field, _), raw, score in zip(cells, result.txts, result.scores):
                normalized, error = normalize_time(raw)
                entry = {'page': page, 'row': row, 'field': field, 'raw': raw,
                         'score': float(score), 'time': normalized if not error else '',
                         'parse_error': error}
                entries.append(entry)
                if raw.strip():
                    print(view, row, field, repr(raw), round(float(score), 4),
                          normalized if not error else 'INVALID', flush=True)
            report['views'].setdefault(view, []).extend(entries)
    report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Saved', output, 'in', report['elapsed_seconds'], 'seconds', flush=True)


if __name__ == '__main__':
    main()
