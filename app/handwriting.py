"""EXPERIMENTAL blue-ink handwritten-digit OCR, with conservative abstention.

The bundled model was trained on individual UCI human-written digit shapes and
rendered A/P suffixes. It has not been validated as reliable on free-flowing
real-world timesheets. This module must NEVER authorize payroll or skip review.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path

MODEL = Path(__file__).resolve().parent / 'assets' / 'handwritten_digit_svc.joblib'


def _glyph_feature(binary):
    import numpy as np
    import cv2
    ys,xs=np.nonzero(binary)
    if not len(xs): return np.zeros((256,),dtype='float32')
    arr=(binary[ys.min():ys.max()+1,xs.min():xs.max()+1]*255).astype('uint8')
    h,w=arr.shape
    tw=max(1,round(w*12/max(w,h)))
    th=max(1,round(h*12/max(w,h)))
    tile=cv2.resize(arr,(tw,th),interpolation=cv2.INTER_AREA)
    center=np.zeros((16,16),dtype='uint8')
    cx=(16-tw)//2;cy=(16-th)//2
    center[cy:cy+th,cx:cx+tw]=tile
    return center.reshape(-1).astype('float32')/255.0


@lru_cache(maxsize=1)
def _model():
    import joblib
    if not MODEL.is_file():
        raise FileNotFoundError('Handwritten-digit model missing from application')
    return joblib.load(MODEL)


def _components(image):
    import numpy as np
    import cv2
    a=np.asarray(image.convert('RGB'))
    r,g,b=[a[:,:,i].astype('int16') for i in range(3)]
    mask=np.uint8((b-r>19)&(b-g>7)&(b<248))*255
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask)
    components=[]
    for i in range(1,n):
        x,y,w,h,p=[int(v) for v in stats[i]]
        if p>=15 and h>=10 and w>=3:
            components.append((x, _glyph_feature(labels[y:y+h,x:x+w]==i)))
    components.sort(key=lambda item:item[0])
    return [ft for _,ft in components]


def recognize_time(image, minimum_confidence:float=0.90)->tuple[str,float,str]:
    """Return suggested time (AM/PM), min glyph confidence, status.

    An empty suggestion means abstain. 'uncertain' is expected and must
    not be treated as a blank/no-shift cell by the review workflow.
    """
    from .core import normalize_time
    try:
        comps=_components(image)
        if not comps:
            return '',0.,'no-visible-blue-ink'
        if len(comps)>6:
            return '',0.,'too-many-components'
        model=_model()
        import numpy as np
        probs=model.predict_proba(np.asarray(comps,dtype='float32'))
        indices=np.argmax(probs,axis=1)
        text=''.join(str(model.classes_[i]) for i in indices)
        confidence=float(np.min(probs[np.arange(len(indices)),indices]))
        _,error=normalize_time(text)
        if error:
            return '',confidence,f'unreadable:{text}'
        if confidence < minimum_confidence:
            return '',confidence,f'uncertain:{text}'
        return text,confidence,'ok'
    except (ImportError,FileNotFoundError,OSError) as exc:
        return '',0.,'engine-unavailable:'+type(exc).__name__
