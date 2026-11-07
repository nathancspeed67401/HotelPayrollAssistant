import pytest
from app.benchmark import evaluate_cells


def label(**changes):
    value={'sheet':'S01','row':0,'field':'in1','literal':'8:30A','status':'written',
           'split':'holdout','transcriber_id':'first','reviewer_id':'second','independently_verified':True}
    return value|changes


def test_missing_predictions_are_misses_and_never_dropped():
    result=evaluate_cells([label()],[],1)
    assert result['counts']['missed_transcriptions']==1
    assert result['exact_transcription_accuracy']==0
    assert not result['target_met']


@pytest.mark.parametrize('change',[{'reviewer_id':'first'},{'independently_verified':False},{'split':'development'}])
def test_a_development_result_or_unchecked_label_cannot_meet_release_target(change):
    prediction={'sheet':'S01','row':0,'field':'in1','raw':'8:30A','value':'8:30A'}
    result=evaluate_cells([label(**change)],[prediction],1)
    assert result['exact_transcription_accuracy']==1
    assert not result['target_met']


def test_blank_false_positives_and_ambiguity_are_counted_separately():
    labels=[label(status='blank',literal=''),label(row=1,status='ambiguous',literal=None)]
    predictions=[{'sheet':'S01','row':i,'field':'in1','raw':'8:30A','value':'8:30A'} for i in (0,1)]
    result=evaluate_cells(labels,predictions,2)
    assert result['counts']['false_populated_blanks']==1
    assert result['counts']['proposals_on_ambiguous']==1


def test_missing_cells_cannot_be_omitted_from_an_accuracy_claim():
    prediction={'sheet':'S01','row':0,'field':'in1','raw':'8:30A','value':'8:30A'}
    result=evaluate_cells([label()],[prediction],28)
    assert result['exact_transcription_accuracy']==1
    assert not result['complete'] and not result['target_met']
