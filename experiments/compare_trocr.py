"""Evaluate a predownloaded Microsoft TrOCR model with networking denied."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.offline_guard import block_network


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--model-dir', required=True)
    parser.add_argument('--registered', action='store_true')
    parser.add_argument('--views', nargs='+', default=['raw', 'blue-tight'])
    args = parser.parse_args()
    block_network()
    import numpy as np
    import torch
    from PIL import Image
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    from app.core import normalize_time
    from app.ocr import load_pages
    from experiments.compare_line_ocr import clock_cells, prepare

    torch.set_num_threads(2)
    processor = TrOCRProcessor.from_pretrained(args.model_dir, local_files_only=True,
                                               use_fast=False)
    model = VisionEncoderDecoderModel.from_pretrained(args.model_dir,
                                    local_files_only=True, weights_only=True).eval()
    report = {'model_dir': args.model_dir, 'views': {}, 'registered': args.registered,
              'purpose': 'development experiment; no independent accuracy claim'}
    started = time.perf_counter()
    for page, image in enumerate(load_pages(args.input), 1):
        cells = clock_cells(image, args.registered)
        for view in args.views:
            output = []
            for offset in range(0, len(cells), 4):
                batch = cells[offset:offset+4]
                images = [Image.fromarray(prepare(cell, view)[:, :, ::-1])
                          for _, _, cell in batch]
                pixels = processor(images=images, return_tensors='pt').pixel_values
                with torch.inference_mode():
                    generated = model.generate(pixels, max_new_tokens=16, num_beams=1,
                        return_dict_in_generate=True, output_scores=True)
                    scores = model.compute_transition_scores(generated.sequences,
                        generated.scores, normalize_logits=True).exp().numpy()
                strings = processor.batch_decode(generated.sequences, skip_special_tokens=True)
                for i, ((row, field, _), raw) in enumerate(zip(batch, strings)):
                    normalized, error = normalize_time(raw)
                    token_scores = []
                    tokens = generated.sequences[i,1:].tolist()
                    for token, probability in zip(tokens, scores[i]):
                        if token == model.config.pad_token_id:
                            break
                        token_scores.append(float(probability))
                        if token == model.config.eos_token_id:
                            break
                    confidence = min(token_scores) if token_scores else 0.
                    output.append({'page': page, 'row': row, 'field': field,
                        'raw': raw, 'score': confidence,
                        'time': normalized if not error else '', 'parse_error': error})
                    if raw.strip():
                        print(view, row, field, repr(raw), round(confidence,4),
                              normalized if not error else 'INVALID', flush=True)
            report['views'].setdefault(view, []).extend(output)
    report['elapsed_seconds'] = round(time.perf_counter()-started,3)
    path = Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Saved', path, 'in', report['elapsed_seconds'], 'seconds', flush=True)


if __name__ == '__main__':
    main()
