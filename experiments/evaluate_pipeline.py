"""Evaluate scan_page suggestions separately from accepted punch fields."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.offline_guard import block_network
block_network()
from app.core import TIME_FIELDS, normalize_time
from app.ocr import load_pages, scan_page


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    manifest = Path(a.manifest)
    ground = json.loads(manifest.read_text())
    if isinstance(ground, dict):
        entries = [{f: '' for f in TIME_FIELDS} for _ in range(14)]
        for cell in ground['cells']:
            entries[cell['row']][cell['field']] = cell['written']
        ground = [dict(file=ground['source'], punches=entries)]
    totals = dict(correct=0, missed=0, wrong=0, blank=0, false_positive=0,
                  ambiguous=0, ambiguous_auto_filled=0, ambiguous_suggestions=0, auto_filled=0)
    reports = []
    started = time.perf_counter()
    for index, case in enumerate(ground):
        path = manifest.parent/case['file']
        image = load_pages(str(path))[0]
        sheet = scan_page(str(path), image)
        counts = dict.fromkeys(totals, 0)
        mistakes = []
        for row, day in enumerate(case['punches']):
            for field in TIME_FIELDS:
                written = day[field]
                expected, error = normalize_time(written)
                scanned = sheet.days[row]
                filled = bool(getattr(scanned, field))
                counts['auto_filled'] += filled
                got = scanned.observations.get(field, {}).get('proposal', '')
                actual, actual_error = normalize_time(got)
                if not written:
                    counts['blank'] += 1
                    counts['false_positive'] += bool(got)
                elif error:
                    counts['ambiguous'] += 1
                    counts['ambiguous_auto_filled'] += filled
                    counts['ambiguous_suggestions'] += bool(got)
                elif actual == expected and not actual_error:
                    counts['correct'] += 1
                elif not got:
                    counts['missed'] += 1
                else:
                    counts['wrong'] += 1
                if (written and not error and expected != actual) or ((not written or error) and got):
                    mistakes.append(dict(row=row, field=field, expected=written,
                        actual=got, raw=sheet.days[row].recognized.get(field, '')))
        for key, value in counts.items():
            totals[key] += value
        reports.append(dict(case=index+1, counts=counts, mismatches=mistakes))
        print('case', index+1, counts, flush=True)
    report = dict(totals=totals, cases=reports, elapsed_seconds=round(time.perf_counter()-started, 3))
    Path(a.output).write_text(json.dumps(report, indent=2))
    print('TOTAL', totals, report['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
