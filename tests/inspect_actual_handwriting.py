from PIL import Image
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.experimental_digit_reader import train,predict,ROW_Y,COL_X
from app.ocr import _ocr_cell,_cleanup_time,_likely_blank
im=Image.open('/mnt/data/_timesheet_ref.png').convert('RGB')
clf=train()
for i,(top,bottom) in enumerate(ROW_Y):
 print('ROW',i, end=' ')
 for j,(left,right) in enumerate(COL_X[:2]):
  crop=im.crop((left,top+3,right,bottom-3))
  s,meta=predict(clf,crop)
  tess=_cleanup_time(_ocr_cell(crop,'0123456789:APMapm')) if not _likely_blank(crop) else ''
  print(('in' if j==0 else 'out'), 'digit=',s,'confidence=',round(min((m[1] for m in meta),default=0),2),'tess=',repr(tess),end='; ')
 print()
