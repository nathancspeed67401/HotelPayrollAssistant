"""Benchmark sheets: genuine human-written UCI digits, synthetic punctuation/letters.

Digits are copied from sklearn.datasets.load_digits, a UCI real handwriting corpus.
Letters A/P and names are typeset, NOT natural handwriting.
This is regression testing, not training or verified real timesheet accuracy.
"""
from __future__ import annotations
import random,json,sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from sklearn.datasets import load_digits
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ocr import REF_W,REF_H,ROW_Y,COL_X
from app.core import ShiftDay,Sheet,summarize
from tests.generate_synthetic_sheets import blank_form

OUT=Path(__file__).resolve().parents[1]/'test_samples'/'real_digit_benchmark'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf'
TESTS=[
('A01_Day_1', 'Fictional Employee A', {2:['8A','4P','',''],3:['9A','5P','',''],4:['7A','3P','',''],5:['8A','4P','',''],9:['8A','4P','',''],10:['9A','5P','','']}, 'normal'),
('A02_Overnight', 'Fictional Employee B', {1:['11P','7A','',''],2:['12A','8A','',''],3:['12A','8A','',''],4:['10P','6A','',''],8:['12A','8A','',''],9:['11P','7A','','']},'blue'),
('A03_Mixed', 'Fictional Employee C', {1:['9:15A','5:30P','',''],2:['12A','9:15A','',''],4:['2:30P','11P','',''],7:['8A','12P','1P','5P'],10:['8A','4P','','']},'soft'),
('A04_Late', 'Fictional Employee D', {0:['12A','8A','',''],2:['9P','5A','',''],5:['10P','6A','',''],7:['12A','8A','',''],11:['12A','8A','','']},'rotation'),
('A05_Breaks', 'Fictional Employee E', {0:['6:30A','11:30A','12P','3P'],2:['8A','12P','1P','5P'],3:['7A','11A','12P','4P'],9:['10A','2P','3P','7P']},'faded'),
('A06_Blanks', 'Fictional Employee F', {3:['11:45P','7:15A','',''],10:['12P','9:30P','','']},'compression'),
]

def digit_tile(raw:np.ndarray, height:int, tint=(22,44,145))->Image.Image:
    ar=np.clip(np.asarray(raw,dtype='float32')/16,0,1)
    pil=Image.fromarray(np.uint8(255*ar),'L')
    # Dataset is 8x8: upscale with bicubic interpolation. These are genuine
    # digit bitmaps, but their smoothing/assembly into timestamps is synthetic.
    tile=pil.resize((int(height*.67),height),Image.Resampling.BICUBIC)
    gray=np.asarray(tile).astype(np.float32)/255
    alpha=np.uint8(255*np.clip((gray-.13)*1.8,0,1))
    res=Image.new('RGBA',tile.size,(*tint,0));res.putalpha(Image.fromarray(alpha,'L'))
    return res

def add_time(im:Image.Image,text:str,pos:tuple[int,int],rng,imgs_by_label,style):
    chars=text.replace(' ','')
    # clock value stays within one input cell, so keep 19-21px tall writing
    start_x,start_y=pos
    height=25 if len(chars)<=4 else 22
    x=start_x; y=start_y
    tint=(27,47,123) if style!='blue' else (10,40,160)
    for ch in chars:
        if ch.isdigit():
            sample=imgs_by_label[int(ch)][rng.randrange(len(imgs_by_label[int(ch)]))]
            tile=digit_tile(sample,height,tint)
            if rng.random()<.5:
                tile=tile.rotate(rng.uniform(-7,7), resample=Image.Resampling.BICUBIC, expand=False)
            im.paste(tile,(round(x),round(y+rng.uniform(-1.5,1.5))),tile)
            x+=tile.width+rng.randint(0,2)
        elif ch==':':
            d=ImageDraw.Draw(im)
            d.ellipse((x+1,y+8,x+3,y+10),fill=tint)
            d.ellipse((x+1,y+17,x+3,y+19),fill=tint)
            x+=7
        else:
            # AM/PM suffix is rendered. 8x8 digit corpus does not include letters.
            draw=ImageDraw.Draw(im)
            draw.text((x-1,y-1),ch,font=ImageFont.truetype(FONT,21),fill=tint)
            x+=16
    return x

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    D=load_digits();images=D.images; labels=D.target
    # Select from indices >= 1100 only; first 1100 kept available as separate
    # potential training pool. Do not contaminate testing with training samples.
    imgs={k:[images[i] for i in range(1100,len(labels)) if labels[i]==k] for k in range(10)}
    rng=random.Random(91824)
    manifest=[];pages=[]
    for k,(slug,name,rows,style) in enumerate(TESTS):
        im=blank_form().convert('RGB')
        d=ImageDraw.Draw(im)
        d.text((597,210),name,font=ImageFont.truetype(FONT,22),fill=(28,45,145))
        for idx,values in rows.items():
            top,bottom=ROW_Y[idx]
            for j,txt in enumerate(values):
                if txt:
                    left,right=COL_X[j]
                    add_time(im,txt,(left+6,top+6),rng,imgs,style)
        if style=='soft': im=im.filter(ImageFilter.GaussianBlur(.40))
        if style=='rotation': im=im.rotate(-.55,Image.Resampling.BICUBIC,expand=False,fillcolor='white')
        if style=='faded': im=ImageEnhance.Contrast(im).enhance(.82)
        if style=='compression':
            from io import BytesIO
            bio=BytesIO();im.save(bio,format='JPEG',quality=65);bio.seek(0);im=Image.open(bio).convert('RGB')
        file=f'{slug}.png'; im.save(OUT/file,optimize=True); pages.append(im)
        days=[]
        for idx in range(14):
            values=rows.get(idx,['','','',''])
            days.append(ShiftDay(*values))
        manifest.append({'file':file,'name':name,'style':style,'punches':[
            {'in1':day.in1,'out1':day.out1,'in2':day.in2,'out2':day.out2} for day in days],
            'expected':summarize(Sheet(str(OUT/file),'fiction',name,'2026-10-24',days=days)),
            'digit_origin':'scikit-learn load_digits indices >=1100, UCI optical handwritten digits',
            'note':'Real human digits; synthetic composition, punctuation, names and AM/PM.'})
    pages[0].save(OUT/'UCI_Digit_Timesheet_Benchmark.pdf',format='PDF',resolution=150,save_all=True,append_images=pages[1:])
    (OUT/'ground_truth.json').write_text(json.dumps(manifest,indent=2))
    (OUT/'DATASET_AND_LIMITATIONS.md').write_text('''# Handwriting benchmark provenance\n\n- Public corpus: scikit-learn bundled `load_digits()` (UCI Optical Recognition of Handwritten Digits), containing 1,797 real human-written 8×8 digit samples.\n- Only samples with index 1100 onward were used to assemble these test forms.\n- Clock times, line layout, employee names, AM/PM suffixes and punctuation were generated. Digits are **genuine but resized and synthetically recombined**; no person physically wrote these complete timesheets.\n- No real employee personal data or times are included.\n- The visual layout matches the same two-week form geometry; this is a re-created blank form, not an unmodified scan.\n- Treat accuracy as regression on this narrow sample; do not use it as a claim of real phone-photo or whole-timesheet accuracy.\n- Source: https://archive.ics.uci.edu/dataset/80/optical%2Brecognition%2Bof%2Bhandwritten%2Bdigits and https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html\n''')
    print('Created',len(manifest),'test sheets:',OUT)
if __name__=='__main__':build()
