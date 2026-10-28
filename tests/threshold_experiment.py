import sys, json
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.experimental_digit_reader import train,predict,OUT,ROW_Y,COL_X
from app.core import normalize_time
clf=train();gold=json.loads((OUT/'ground_truth.json').read_text())
res=[]
for case in gold:
 im=Image.open(OUT/case['file']).convert('RGB')
 for i,day in enumerate(case['punches']):
  t,b=ROW_Y[i]
  for fld,(l,r) in zip(('in1','out1','in2','out2'),COL_X):
   want=day[fld]
   if not want:continue
   s,meta=predict(clf,im.crop((l,t+3,r,b-3)))
   norm,_=normalize_time(s);w,_=normalize_time(want)
   res.append((norm==w and bool(norm),min([m[1] for m in meta] or [0]),want,s))
for threshold in (0.5,.6,.7,.8,.9,.94,.96,.98):
 sel=[x for x in res if x[1]>=threshold]
 print(threshold,'Accepted',len(sel),'Correct',sum(x[0] for x in sel),'Wrong',sum(not x[0] for x in sel),'Accuracy',round(100*sum(x[0] for x in sel)/max(len(sel),1),1))
