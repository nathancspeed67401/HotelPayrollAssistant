"""Run the actual importer on private photos under an offline process guard."""
from pathlib import Path
import argparse,hashlib,io,json,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def variant(image,name):
    from PIL import Image,ImageEnhance
    if name=='original':return image
    if name=='rotate180':return image.transpose(Image.Transpose.ROTATE_180)
    if name=='dim':return ImageEnhance.Brightness(image).enhance(.62)
    if name=='jpeg45':
        buffer=io.BytesIO();image.save(buffer,'JPEG',quality=45);buffer.seek(0)
        with Image.open(buffer) as decoded:return decoded.convert('RGB')
    import cv2
    import numpy as np
    w,h=image.size
    source=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
    target=np.float32([[.035*w,.016*h],[.97*w,0],[w-1,.98*h],[0,h-1]])
    matrix=cv2.getPerspectiveTransform(source,target)
    return Image.fromarray(cv2.warpPerspective(np.asarray(image),matrix,(w,h),borderValue=(173,142,109)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--originals',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--source-sha',required=True)
    parser.add_argument('--split',choices=['development','holdout','historical-development','acceptance'],required=True)
    parser.add_argument('--variant',choices=['original','rotate180','dim','jpeg45','perspective'],default='original')
    parser.add_argument('--sheet',action='append',help='Limit a diagnostic run to anonymous sheet IDs')
    args=parser.parse_args()
    if args.split == 'acceptance' and (args.sheet or args.variant != 'original'):
        parser.error('Acceptance must scan every original in the acceptance split')
    from experiments.offline_guard import block_network
    block_network()
    from app.ocr import scan_page,load_pages
    manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    predictions=[];registration={};started=time.perf_counter()
    for record in manifest['sheets']:
        sid=record['id']
        if record['split']!=args.split or (args.sheet and sid not in args.sheet):continue
        name=record['file']
        if Path(name).name!=name:raise ValueError('Expected a plain original filename')
        source=Path(args.originals)/name
        with source.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=record['original_sha256']:
                raise ValueError(f'{sid}: source does not match the original archive')
        pages=load_pages(str(source))
        if len(pages)!=1:raise ValueError(f'{sid}: expected one image')
        sheet=scan_page(str(source),variant(pages[0],args.variant))
        registration[sid]=sheet.form_type=='comfort_suites_single_pair' and len(sheet.review_boxes)==14
        for row,day in enumerate(sheet.days):
            for field in ('in1','out1'):
                obs=day.observations.get(field,{})
                candidates=obs.get('candidates',[])
                best=obs.get('transcription') or (max(candidates,key=lambda c:c.get('confidence',0))
                                                 if candidates else {})
                predictions.append({'sheet':sid,'row':row,'field':field,
                    'raw':best.get('text',day.recognized.get(field,'')),
                    'value':getattr(day,field),'suggestion':obs.get('proposal',getattr(day,field)),
                    'status':obs.get('status','unknown'),
                    'confidence':best.get('confidence')})
        print('Evaluated',sid,flush=True)
    if not registration:raise ValueError('No sheets selected')
    output={'source_sha':args.source_sha,'split':args.split,'variant':args.variant,
            'seconds':time.perf_counter()-started,'registration':registration,'predictions':predictions}
    Path(args.output).write_text(json.dumps(output,indent=2),encoding='utf-8')


if __name__=='__main__':main()
