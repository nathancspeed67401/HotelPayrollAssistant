"""Collect offline line-model predictions for public benchmark forms."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.sweep_line_views import infer, view_of, ort
from experiments.compare_line_ocr import prepare, clock_cells
from app.ocr import _likely_blank, load_pages
from app.form_geometry import find_form_grid


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(a.model, options, providers=['CPUExecutionProvider'])
    chars = ['blank'] + session.get_modelmeta().custom_metadata_map['character'].splitlines() + [' ']
    manifest = Path(a.manifest)
    report = []
    for case in json.loads(manifest.read_text()):
        image = load_pages(str(manifest.parent/case['file']))[0]
        cells = clock_cells(image, find_form_grid(image) is not None)
        active = [i for i, (_, _, cell) in enumerate(cells) if not _likely_blank(cell)]
        entries = [dict(row=row, field=field, expected=case['punches'][row][field],
                        blank=i not in active, views={}) for i, (row, field, _) in enumerate(cells)]
        for view in ['raw', 'blue', 'tight', 'width0.75', 'thin', 'clean']:
            images = [(prepare(cells[i][2], 'blue') if view == 'blue' else
                       view_of(cells[i][2], view)) for i in active]
            for i, (raw, score, minimum) in zip(active, infer(session, images, chars)):
                entries[i]['views'][view] = dict(raw=raw, score=score, minimum=minimum)
        report.append(dict(file=case['file'], entries=entries))
        print(case['file'], len(active), 'visible cells', flush=True)
    Path(a.output).write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
