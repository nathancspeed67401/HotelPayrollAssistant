"""Summarize a private cell benchmark without exporting employee-level data."""
from pathlib import Path
import argparse,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.benchmark import evaluate_cells


def verify_acceptance(manifest, reference, run):
    """Check the manifest against the previously scored originals and frozen source."""
    source = manifest.get('acceptance_source_sha', '')
    if (run['variant'] != 'original' or source != run['source_sha']
            or not re.fullmatch(r'[0-9a-f]{40}', source)):
        raise ValueError('Acceptance requires original photos and the frozen source SHA')
    sheets = manifest['sheets']
    previous = {s['original_sha256']: s['split'] for s in reference['sheets']}
    splits = {s['original_sha256']: s['split'] for s in sheets}
    if (not previous or len(splits) != len(sheets)
            or any(splits.get(digest) != split for digest, split in previous.items())):
        raise ValueError('Preserve the reference originals and split; every photo hash must be unique')
    writers = {'prior': set(), 'acceptance': set()}
    expected_cells = {(row, field) for row in range(14) for field in ('in1', 'out1')}
    for sheet in sheets:
        writer = sheet.get('writer_id')
        if not isinstance(writer, str) or not writer.strip():
            raise ValueError('Writer IDs are required for all reference and acceptance sheets')
        if sheet['split'] == 'acceptance':
            cells = {(c['row'], c['field']) for c in sheet['cells']}
            if cells != expected_cells or len(sheet['cells']) != len(expected_cells):
                raise ValueError('Acceptance requires both punches for all 14 rows, including blanks')
            writers['acceptance'].add(writer.strip())
        else:
            writers['prior'].add(writer.strip())
    if not writers['acceptance'] or writers['prior'] & writers['acceptance']:
        raise ValueError('Acceptance writers must be disjoint from prior writers')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--predictions',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--split',choices=['development','holdout','acceptance'],required=True)
    parser.add_argument('--reference-manifest',help='Prior frozen manifest, required for acceptance')
    args=parser.parse_args()
    manifest=json.loads(Path(args.manifest).read_text())
    sheets=[s for s in manifest['sheets'] if s['split']==args.split]
    labels=[dict(c,sheet=s['id'],split=s['split']) for s in sheets for c in s['cells']]
    run=json.loads(Path(args.predictions).read_text())
    if run['split'] != args.split:
        raise ValueError('Predictions and requested evaluation split do not match')
    acceptance = args.split == 'acceptance'
    if acceptance:
        if not args.reference_manifest:
            parser.error('--reference-manifest is required for acceptance')
        verify_acceptance(manifest, json.loads(Path(args.reference_manifest).read_text()), run)
    ids={s['id'] for s in sheets}
    keys = {(item['sheet'], item['row'], item['field']) for item in labels}
    registration = run['registration']
    scored = [item | {'status': 'alignment-failed'} if registration.get(item['sheet']) is False else item
              for item in run['predictions'] if (item['sheet'], item['row'], item['field']) in keys]
    result=evaluate_cells(labels,scored,len(sheets)*28,acceptance_verified=acceptance)
    result['sheets'] = {'registered': sum(registration.get(sid) is True for sid in ids),
                        'failed_registration': sum(registration.get(sid) is False for sid in ids),
                        'unscanned': sum(sid not in registration for sid in ids)}
    result['target_met'] &= result['sheets']['registered'] == len(ids)
    result['source_sha'] = run['source_sha']
    result['variant'] = run['variant']
    result['source']='private supplied photographs; labels must be independently checked'
    Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
