"""Create fictional test timesheets with a layout matching the user's paper form.

No real employee names, times or photographs included. Synthetic pen-like fonts
are NOT evidence of accuracy on actual handwriting or phone camera photos.
"""
from __future__ import annotations
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core import ShiftDay, Sheet, summarize
from app.ocr import REF_H, REF_W, ROW_Y, COL_X

BASE = Path(__file__).resolve().parents[1] / 'test_samples'
FONTS = [
 '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf',
 '/usr/share/fonts/truetype/lato/Lato-MediumItalic.ttf',
 '/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf',
 '/usr/share/fonts/opentype/urw-base35/URWBookman-LightItalic.otf',
]
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def font(size: int, variation: int=0):
    path = FONTS[variation%len(FONTS)]
    return ImageFont.truetype(path, size)

def print_font(size:int, bold:bool=False):
    return ImageFont.truetype(BOLD, size)

def blank_form():
    canvas = Image.new('RGB', (REF_W,REF_H), (251,251,248))
    d = ImageDraw.Draw(canvas)
    ink=(37,42,51); grid=(155,162,169)
    # Form proportions copied from sample; positions align with the app crop geometry.
    xs=[75,213,345,478,607,745,919]
    d.rectangle((74,109,920,1187),outline=grid,width=2)
    for y in [166,205,245,285,323,362,405,444,483,522,561,600,638,674,713,751,789,827,865,903,941,981,1028,1073]:
        d.line((75,y,919,y), fill=grid, width=1)
    d.line((502,166,502,323),fill=grid,width=1)
    for k in range(2):
        for x in xs[1:-1]:
            d.line((x,323 if k==0 else 638,x,638 if k==0 else 941), fill=grid,width=1)
    d.text((364,117),'Bi-Weekly Timesheet',font=print_font(26),fill=ink)
    d.text((202,176),'715 W Schilling Road',font=print_font(16),fill=ink)
    d.text((650,174),'Employee Name:',font=print_font(16),fill=ink)
    d.text((251,215),'Salina Kansas',font=print_font(16),fill=ink)
    d.text((602,251),'General Manager:',font=print_font(15),fill=ink)
    d.text((239,252),'785-404-6944',font=print_font(15),fill=ink)
    d.text((266,291),'Week Of:',font=print_font(15),fill=ink)
    d.text((638,291),'Week Ending:',font=print_font(15),fill=ink)
    cols=['Day of Week','Time In','Time Out','Time In','Time Out','Total']
    starts=[92,242,366,510,646,806]
    for y in (333,645):
        for s,x in zip(cols,starts):
            d.text((x,y),s,font=print_font(15),fill=ink)
    days=['SAT','SUN','MON','TUES','WED','THURS','FRI']
    for j in range(2):
        for i,name in enumerate(days):
            top,_ = ROW_Y[j*7+i]
            d.text((83,top+7),name,font=print_font(14),fill=ink)
    d.text((94,946),'Week 1 Total Hours',font=print_font(15),fill=ink)
    d.text((494,946),'Week 2 Total Hours',font=print_font(15),fill=ink)
    d.text((87,987),'Employee Signature:',font=print_font(14),fill=ink)
    d.text((87,1035),'General Manager Signature:',font=print_font(14),fill=ink)
    d.text((87,1080),'Notes:',font=print_font(14),fill=ink)
    return canvas

# Realistic structured schedule test cases, including intentional validation failures.
# Blank days are simply not included in the punch dictionary.
CASES=[
 ('01_Daytime', 'Avery Wilson', {i:['8A','4P','',''] for i in (2,3,4,5,6,9,10,11,12,13)}, 'clean'),
 ('02_Overnight', 'Jordan Miles', {i:['12A','8A','',''] for i in (2,3,4,5,6,9,10,11)}, 'blue_ink'),
 ('03_SplitShifts', 'Morgan Bennett', {i:['8A','12P','1P','5P'] for i in (1,2,3,4,5,8,9,10)}, 'clean'),
 ('04_Overtime', 'Taylor Collins', {**{i:['8A','4P','',''] for i in (0,1,2,3,4,5)}, **{i:['8A','5P','',''] for i in (7,8,9,10,11)}}, 'clean'),
 ('05_MixedShifts', 'Casey Brooks', {0:['3P','11P','',''],1:['11P','7A','',''],3:['12A','4A','',''],7:['2:30A','10A','',''],10:['12P','9:15P','','']}, 'blue_ink'),
 ('06_MultipleFonts','Drew Parker',{1:['7:45A','3:15P','',''],2:['11:30P','7:30A','',''],3:['6A','10A','10:30A','2:30P'],8:['9A','5:30P','',''],10:['2P','11P','','']},'rotated'),
 ('07_MissingPunch','Riley Hayes',{2:['8A','','',''],9:['12A','8A','','']},'clean'),
 ('08_AmbiguousTime','Sam Ellis',{1:['9:15','5P','',''],10:['8A','4P','','']},'faded'),
 ('09_PhonePhoto','Alex Rivera',{0:['9A','5P','',''],3:['12A','8A','',''],4:['12A','8A','',''],7:['7A','3P','',''],10:['9P','5A','','']},'phone'),
 ('10_Blank', 'Jamie Quinn', {},'clean'),
]

def create():
    BASE.mkdir(parents=True,exist_ok=True)
    images=[]; ground=[]
    for idx,(slug,name,entries,style) in enumerate(CASES):
        rand=random.Random(350+idx)
        canvas=blank_form()
        d=ImageDraw.Draw(canvas)
        handwritten=(24,42,145) if style in ('blue_ink','faded','phone') else (28,53,136)
        d.text((604,211),name,font=font(31,idx),fill=handwritten)
        days=[ShiftDay(**{k:(entries.get(i,['','','',''])[j]) for j,k in enumerate(('in1','out1','in2','out2'))}) for i in range(14)]
        for i,day in enumerate(days):
            top,bottom=ROW_Y[i]
            for j,(left,right) in enumerate(COL_X):
                val=getattr(day,('in1','out1','in2','out2')[j])
                if not val:continue
                size=29 if len(val)<=4 else (26 if len(val)<=6 else 23)
                shift_y=rand.randint(-2,2)
                f=font(size,idx+j)
                d.text((left+5,top+3+shift_y),val,font=f,fill=handwritten,stroke_width=0)
        if style=='faded':
            canvas=ImageEnhance.Contrast(canvas).enhance(.76)
            canvas=ImageEnhance.Brightness(canvas).enhance(1.06)
        elif style=='phone':
            canvas=ImageEnhance.Contrast(canvas).enhance(.85)
            canvas=canvas.filter(ImageFilter.GaussianBlur(.45))
            canvas=canvas.rotate(-1.6,resample=Image.Resampling.BICUBIC,expand=False,fillcolor=(247,247,243))
        elif style=='rotated':
            canvas=canvas.rotate(1.0,resample=Image.Resampling.BICUBIC,expand=False,fillcolor=(252,252,252))
        target=BASE/(slug+'.png')
        canvas.save(target,optimize=True)
        images.append(canvas)
        rec=Sheet(str(target), 'synthetic', name, '2026-10-24', days=days)
        ground.append({'file':target.name,'name':name,'style':style,'expected':summarize(rec),'punches':[vars(v) for v in days],
          'valid_expected':slug not in ('07_MissingPunch','08_AmbiguousTime')})
    pdf=BASE/'Synthetic_Test_Timesheets.pdf'
    images[0].save(pdf,'PDF',resolution=150,save_all=True,append_images=images[1:])
    (BASE/'ground_truth.json').write_text(json.dumps(ground,indent=2),encoding='utf-8')
    return ground
if __name__=='__main__':
    print('Generated',len(create()),'fictional forms at',BASE)
