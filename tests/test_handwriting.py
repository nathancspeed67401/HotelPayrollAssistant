"""Small, fast OCR safety/regression checks using held-out real human digits."""
import json
from pathlib import Path
from PIL import Image
from app.handwriting import recognize_time, MODEL
from app.ocr import COL_X,ROW_Y
from app.core import normalize_time

BASE=Path(__file__).resolve().parents[1]/'test_samples'/'real_digit_benchmark'

def _canonical(text):
    value,error=normalize_time(text)
    return value if not error else None

def test_model_is_packaged():
    assert MODEL.is_file() and MODEL.stat().st_size>5000

def test_blank_does_not_fabricate_shift():
    value,confidence,status=recognize_time(Image.new('RGB',(120,35),'white'))
    assert value=='' and status=='no-visible-blue-ink'

def test_high_confidence_heldout_real_digit_samples():
    # Uses genuine digit images NOT in model's digit training split. AM/PM
    # suffixes and completed clock entries are synthetically composed.
    samples=json.loads((BASE/'ground_truth.json').read_text())
    evaluated=accepted=wrong=0
    for sample in samples:
        im=Image.open(BASE/sample['file']).convert('RGB')
        for i,day in enumerate(sample['punches']):
            top,bottom=ROW_Y[i]
            for field,(left,right) in zip(('in1','out1','in2','out2'),COL_X):
                expected=day[field]
                if not expected:continue
                evaluated+=1
                crop=im.crop((left,top+3,right,bottom-3))
                candidate,confidence,status=recognize_time(crop)
                if candidate:
                    accepted+=1
                    if _canonical(candidate)!=_canonical(expected):wrong+=1
                    assert confidence>=.90
                    assert status=='ok'
    assert evaluated==66
    assert accepted>=20
    assert wrong==0
