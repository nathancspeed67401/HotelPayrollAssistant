"""Evaluate all genuine-UCI-digit synthetic clock punches against known truth."""
import json,sys,collections
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ocr import scan_page
from app.core import normalize_time
P=Path(__file__).resolve().parents[1]/'test_samples'/'real_digit_benchmark'

def canon(x):
 y,e=normalize_time(x)
 return y if not e else x.strip().upper()

def main():
 ground=json.loads((P/'ground_truth.json').read_text())
 cases=[];hits=misses=wrong=empty=fp=0
 for case in ground:
  fn=P/case['file']
  im=Image.open(fn)
  result=scan_page(str(fn),im)
  b={'file':case['file'],'correct':0,'missed':0,'wrong':0,'false_positive':0,'mismatches':[]}
  for j,expected in enumerate(case['punches']):
   for fld in ('in1','out1','in2','out2'):
    want=expected[fld];got=getattr(result.days[j],fld)
    if want:
     if canon(want)==canon(got):b['correct']+=1;hits+=1
     elif not got:b['missed']+=1;misses+=1
     else:b['wrong']+=1;wrong+=1
     if canon(want)!=canon(got):b['mismatches'].append([j,fld,want,got,result.days[j].recognized.get(fld,'')])
    else:
     empty+=1
     if got: b['false_positive']+=1;fp+=1
  cases.append(b)
  print(fn.name,b['correct'],b['missed'],b['wrong'],b['false_positive'],flush=True)
 report={'filled':hits+misses+wrong,'correct':hits,'missed':misses,'wrong':wrong,'blank':empty,'false_positive':fp,'accuracy_percent':round(100*hits/max(1,hits+misses+wrong),2),'cases':cases}
 (P/'ocr_evaluation.json').write_text(json.dumps(report,indent=2))
 print('REPORT',repr({k:v for k,v in report.items() if k!='cases'}),flush=True)
if __name__=='__main__':main()
