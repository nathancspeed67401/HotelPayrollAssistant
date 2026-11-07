"""Run a predownloaded TrOCR model on private crops, with networking denied.

This emits predictions, not ground truth or an accuracy claim. Never commit
the input manifest, private crops or detailed outputs to the repository.
"""
from pathlib import Path
import argparse
import json
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--crops',required=True)
    parser.add_argument('--model-dir',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--split',choices=['development','holdout'],default='development')
    args = parser.parse_args()
    from experiments.offline_guard import block_network
    block_network()
    import torch
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    from PIL import Image
    from experiments.compare_trocr import minimum_token_confidence
    torch.set_num_threads(2)
    torch.manual_seed(0)
    processor = TrOCRProcessor.from_pretrained(args.model_dir,local_files_only=True,use_fast=False)
    model = VisionEncoderDecoderModel.from_pretrained(args.model_dir,local_files_only=True).eval()
    manifest = json.loads(Path(args.manifest).read_text())
    output = []
    started = time.perf_counter()
    for sheet in manifest['sheets']:
        if sheet['split'] != args.split or not sheet['cells']:
            continue
        files = sorted((Path(args.crops)/sheet['id']).glob('[0-9]*_*.png'))
        for offset in range(0,len(files),4):
            batch = files[offset:offset+4]
            images = [Image.open(p).convert('RGB') for p in batch]
            pixels = processor(images=images,return_tensors='pt').pixel_values
            with torch.inference_mode():
                generated = model.generate(pixels,max_new_tokens=16,num_beams=1,
                    return_dict_in_generate=True,output_scores=True)
                scores = model.compute_transition_scores(generated.sequences,generated.scores,
                                                        normalize_logits=True).exp().numpy()
            texts = processor.batch_decode(generated.sequences,skip_special_tokens=True)
            for i,(path,text) in enumerate(zip(batch,texts)):
                minimum = minimum_token_confidence(generated.sequences[i,1:].tolist(),scores[i],
                    model.generation_config.pad_token_id,model.generation_config.eos_token_id)
                output.append({'sheet':sheet['id'],'cell':path.stem,'text':text,'minimum':minimum})
        print('Processed',sheet['id'],flush=True)
    Path(args.output).write_text(json.dumps({'split':args.split,'seconds':time.perf_counter()-started,
        'engine':'microsoft/trocr-base-handwritten (local)','predictions':output},indent=2))


if __name__ == '__main__':
    main()
