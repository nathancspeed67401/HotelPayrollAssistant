"""Summarize a private cell benchmark without exporting employee-level data."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.benchmark import evaluate_cells


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--predictions',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--split',choices=['development','holdout'],required=True)
    args=parser.parse_args()
    manifest=json.loads(Path(args.manifest).read_text())
    sheets=[s for s in manifest['sheets'] if s['split']==args.split]
    labels=[dict(c,sheet=s['id'],split=s['split']) for s in sheets for c in s['cells']]
    predictions=json.loads(Path(args.predictions).read_text())['predictions']
    ids={s['id'] for s in sheets}
    result=evaluate_cells(labels,[p for p in predictions if p['sheet'] in ids],
                          sum(s.get('expected_cells',28) for s in sheets))
    result['source']='private supplied photographs; labels must be independently checked'
    Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
