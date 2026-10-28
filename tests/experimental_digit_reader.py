"""Research-only classifier; not part of installed payroll application."""
from pathlib import Path
import sys,json,random
import numpy as np,cv2
from PIL import Image, ImageDraw,ImageFont
from sklearn.datasets import load_digits
from sklearn.svm import SVC
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.generate_real_handwriting_sheets import digit_tile, FONT,OUT
from app.ocr import ROW_Y,COL_X
from app.core import normalize_time
D=load_digits()
rng=random.Random(127)

def feat(binary):
    ys,xs=np.nonzero(binary)
    if not len(xs):return np.zeros((16,16),np.float32).flatten()
    arr=(binary[max(0,ys.min()):ys.max()+1,max(0,xs.min()):xs.max()+1] * 255).astype('uint8')
    h,w=arr.shape
    tw=max(1,round(w*12/max(w,h)));th=max(1,round(h*12/max(w,h)))
    stretched=cv2.resize(arr,(tw,th),interpolation=cv2.INTER_AREA)
    center=np.zeros((16,16),np.uint8)
    cx=(16-tw)//2;cy=(16-th)//2
    center[cy:cy+th,cx:cx+tw]=stretched
    return center.flatten()/255.

def isolated_digit(image):
    rgba=digit_tile(image,25)
    return np.asarray(rgba.getchannel('A'))>40

def isolated_letter(char,rotation=0):
    image=Image.new('L',(45,45),0)
    d=ImageDraw.Draw(image)
    d.text((5,1),char,font=ImageFont.truetype(FONT,21),fill=255)
    if rotation:
        image=image.rotate(rotation,Image.Resampling.BICUBIC)
    return np.asarray(image)>40

def train():
    X=[];y=[]
    for i in range(1100):
      for angle in (0,):
        arr=isolated_digit(D.images[i]); X.append(feat(arr));y.append(str(int(D.target[i])))
    for c in 'AP':
      for angle in list(range(-12,13,2))*40:
        X.append(feat(isolated_letter(c,angle)));y.append(c)
    clf=SVC(C=7,gamma=.012,probability=True)
    clf.fit(np.array(X),np.array(y))
    return clf

def components(img):
    a=np.asarray(img.convert('RGB'))
    r,g,b=[a[:,:,i].astype('int16') for i in range(3)]
    mask=np.uint8((b-r>19)&(b-g>7)&(b<248))*255
    n,labels,stats,c=cv2.connectedComponentsWithStats(mask)
    box=[]
    for i in range(1,n):
      x,y,w,h,p=[int(v) for v in stats[i]]
      if p>=15 and h>=10 and w>=3:
        box.append((x,y,w,h,p,i,feat(labels[y:y+h,x:x+w]==i)))
    box.sort(key=lambda x:x[0])
    return box

def predict(clf,img):
    comps=components(img)
    if not comps:return '',[]
    out=[]; meta=[]
    for comp in comps:
      scores=clf.predict_proba(comp[-1].reshape(1,-1))[0]
      scores_order=np.argsort(scores)[::-1]
      classes=clf.classes_;label=classes[scores_order[0]]
      out.append(label);meta.append((label,round(float(scores[scores_order[0]]),2),classes[scores_order[1]],round(float(scores[scores_order[1]]),2)))
    return ''.join(out),meta

def main():
 clf=train()
 gold=json.loads((OUT/'ground_truth.json').read_text())
 filled=hit=invalid=0
 for case in gold:
  im=Image.open(OUT/case['file']).convert('RGB')
  for idx,day in enumerate(case['punches']):
   top,bottom=ROW_Y[idx]
   for fld,(left,right) in zip(('in1','out1','in2','out2'),COL_X):
    want=day[fld]
    if not want:continue
    filled+=1
    crop=im.crop((left,top+3,right,bottom-3))
    s,meta=predict(clf,crop)
    wc,_=normalize_time(want); got,err=normalize_time(s)
    if wc==got and not err:hit+=1
    else:
        invalid+=1
        print(case['file'],idx,fld,want,repr(s),meta,flush=True)
 print('SCORE',hit,filled,round(hit/filled*100,1))

if __name__=='__main__':main()
