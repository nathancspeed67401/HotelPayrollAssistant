"""Reproducible OCR benchmark vs fictional ground truth. Requires Tesseract."""
import csv
import json
import sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core import calculate_day,normalize_time,ShiftDay,Sheet,summarize,validate_sheet
from app.ocr import scan_page

FOLDER=Path(__file__).resolve().parents[1] / 'test_samples'


def comparable(txt):
    val,err=normalize_time(txt)
    return val if not err else txt.strip().upper()

def evaluate():
    gold=json.loads((FOLDER/'ground_truth.json').read_text(encoding='utf-8'))
    rows=[]; punch_total=punch_hit=punch_missed=punch_wrong=empty_total=empty_wrong=0
    reports=[]
    for case in gold:
        fn=FOLDER/case['file']
        with Image.open(fn) as image:
            actual=scan_page(str(fn),image.convert('RGB'))
        expected=Sheet('synthetic','ground',case['name'],'2026-10-24',days=[ShiftDay(**v) for v in case['punches']])
        active=correct=missed=wrong=blanks=false_pos=0
        compare=[]
        for i,(want,got) in enumerate(zip(expected.days,actual.days)):
            for field in ('in1','out1','in2','out2'):
                w=getattr(want,field); g=getattr(got,field)
                if w:
                    active+=1;punch_total+=1
                    if comparable(w)==comparable(g):correct+=1;punch_hit+=1
                    elif not g:missed+=1;punch_missed+=1
                    else:wrong+=1;punch_wrong+=1
                else:
                    blanks+=1;empty_total+=1
                    if g:false_pos+=1;empty_wrong+=1
                if (w or g) and comparable(w)!=comparable(g):
                    compare.append({'row':i+1,'field':field,'expected':w,'read':g,'ocr':got.recognized.get(field,'')})
        est=summarize(actual)
        validation=validate_sheet(actual)
        reports.append({'file':fn.name,'scenario':case['style'],'name_expected':case['name'],'name_read':actual.employee,
                        'name_correct':case['name'].casefold()==actual.employee.casefold().strip(),
                        'filled':active,'correct':correct,'missed':missed,'wrong_valid':wrong,'false_positive':false_pos,
                        'expected_hours':case['expected'],'ocr_hours':est,'validation_warnings':validation,'mismatches':compare})
        rows.append({k:v for k,v in reports[-1].items() if k in ['file','scenario','name_correct','filled','correct','missed','wrong_valid','false_positive']})
        print(f"{fn.name:23s} punches {correct:2d}/{active:2d}; missed={missed:2d} wrong={wrong:2d} false+={false_pos:2d}; name={actual.employee!r}",flush=True)
    result={'punches_filled':punch_total,'correct_filled':punch_hit,'missed_filled':punch_missed,'incorrect_filled':punch_wrong,
            'blank_fields':empty_total,'false_positive_valid_times':empty_wrong,
            'exact_filled_accuracy_percent':round(100*punch_hit/punch_total,2),
            'valid_false_positive_percent':round(100*empty_wrong/empty_total,2),'cases':reports}
    (FOLDER/'ocr_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (FOLDER/'ocr_summary.csv').open('w',newline='',encoding='utf-8') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(f"TOTAL exact={punch_hit}/{punch_total} ({result['exact_filled_accuracy_percent']}%) false valid={empty_wrong}/{empty_total} blanks")
    return result

if __name__=='__main__':evaluate()
