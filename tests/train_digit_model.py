"""Offline deterministic model build (not needed by end users)."""
import sys,random
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from sklearn.datasets import load_digits
from sklearn.svm import SVC
import joblib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.handwriting import _glyph_feature,MODEL
from tests.generate_real_handwriting_sheets import digit_tile,FONT


def train():
    data=load_digits();rng=random.Random(127)
    xs=[];ys=[]
    for i in range(1100):
        glyph=digit_tile(data.images[i],25)
        xs.append(_glyph_feature(np.asarray(glyph.getchannel('A'))>40))
        ys.append(str(int(data.target[i])))
    for char in 'AP':
        for angle in list(range(-12,13,2))*40:
            im=Image.new('L',(45,45),0)
            ImageDraw.Draw(im).text((5,1),char,font=ImageFont.truetype(FONT,21),fill=255)
            if angle:
                im=im.rotate(angle,Image.Resampling.BICUBIC)
            xs.append(_glyph_feature(np.asarray(im)>40));ys.append(char)
    model=SVC(C=7,gamma=.012,probability=True,random_state=22)
    model.fit(np.array(xs),np.array(ys))
    MODEL.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,MODEL,compress=5)
    print('Model stored:',MODEL,'bytes=',MODEL.stat().st_size)
if __name__=='__main__':train()
