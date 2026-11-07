"""Private real-cell evaluation; no images, names or predictions in summaries."""
from collections import Counter
from .line_ocr import clock_key
from .core import normalize_time


def evaluate_cells(labels, predictions, expected_count):
    """Missing predictions count as misses; ambiguous labels never become truth.

    Verification metadata is an explicit reviewer attestation, not a substitute
    for the underlying visual check. A development split cannot meet the gate.
    """
    by_key={}
    for item in predictions:
        key=(item['sheet'],item['row'],item['field'])
        if key in by_key:raise ValueError('Duplicate prediction cell')
        by_key[key]=item
    seen=set();counts=Counter();bins={};verified=True;holdout=True
    for label in labels:
        key=(label['sheet'],label['row'],label['field'])
        if key in seen:raise ValueError('Duplicate ground-truth cell')
        seen.add(key)
        reviewer=label.get('reviewer_id','')
        verified &= (label.get('independently_verified') is True and bool(reviewer)
                     and reviewer != label.get('transcriber_id',''))
        holdout &= label.get('split') == 'holdout'
        predicted=by_key.get(key,{})
        raw=predicted.get('raw','');value=predicted.get('value','')
        literal=label.get('literal');status=label['status']
        if status in ('ambiguous','unreadable','correction'):
            counts['ambiguous']+=1
            if value:counts['proposals_on_ambiguous']+=1
            continue
        if status in ('blank','struck-out-blank'):
            counts['blank']+=1
            if value:counts['false_populated_blanks']+=1
            if clock_key(raw):counts['raw_clock_on_blank']+=1
            continue
        if status != 'written' or not clock_key(literal):
            raise ValueError('Written ground truth requires a readable clock transcription')
        counts['written']+=1
        correct=clock_key(raw)==clock_key(literal)
        counts['exact_transcriptions']+=correct
        if not raw:counts['missed_transcriptions']+=1
        if predicted.get('status')=='blank':counts['false_blank_detections']+=1
        if value:
            expected,error=normalize_time(literal)
            if error or normalize_time(value)[0] != expected:
                counts['wrong_populated_times']+=1
            else:
                counts['correct_populated_times']+=1
        confidence=predicted.get('confidence')
        if isinstance(confidence,(float,int)) and 0 <= confidence <= 1:
            bucket=min(9,int(confidence*10))
            entry=bins.setdefault(bucket,Counter())
            entry['count']+=1;entry['exact']+=correct
    if set(by_key)-seen:raise ValueError('Predictions contain cells absent from ground truth')
    accuracy=counts['exact_transcriptions']/counts['written'] if counts['written'] else None
    payroll_accuracy=counts['correct_populated_times']/counts['written'] if counts['written'] else None
    complete=len(seen)==expected_count and expected_count>0
    return {'cells':len(seen),'expected_cells':expected_count,'counts':dict(counts),
            'exact_transcription_accuracy':accuracy,'independently_verified':bool(verified and complete),
            'exact_populated_punch_accuracy':payroll_accuracy,
            'complete':complete,'holdout':bool(holdout and complete),
            'confidence_bins':{str(k):dict(v) for k,v in bins.items()},
            'target_met':bool(complete and verified and holdout and accuracy is not None and accuracy>=.98
                              and payroll_accuracy is not None and payroll_accuracy>=.98
                              and not counts['wrong_populated_times'] and not counts['false_populated_blanks']
                              and not counts['proposals_on_ambiguous'])}
