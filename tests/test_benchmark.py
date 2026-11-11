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


def test_failed_registration_cannot_get_credit_for_a_coincidental_clock():
    prediction = {'sheet': 'S01', 'row': 0, 'field': 'in1', 'raw': '8:30A',
                  'suggestion': '8:30A', 'status': 'alignment-failed', 'confidence': .99}
    result = evaluate_cells([label()], [prediction], 1)
    counts = result['counts']
    assert counts['missed_transcriptions'] == counts['misses_from_failed_registration'] == 1
    assert counts['exact_transcriptions'] == counts['correct_suggestions'] == 0
    assert counts['unsafe_suggestions'] == 1
    assert not result['confidence_bins']


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


@pytest.mark.parametrize(('literal', 'raw', 'exact'), [
    ('06:45', '6:45', 1),
    ('6A', '6:00A', 0),
    ('6:00A', '6A', 0),
])
def test_raw_scoring_preserves_omitted_minutes_and_rejects_guessed_punches(literal, raw, exact):
    prediction = {'sheet': 'S01', 'row': 0, 'field': 'in1', 'raw': raw, 'value': '06:45'}
    result = evaluate_cells([label(literal=literal)], [prediction], 1)
    assert result['counts']['exact_transcriptions'] == exact
    assert result['counts']['wrong_populated_times'] == 1
    if literal != '6:00A':
        assert result['counts']['eligible_written'] == 0


def test_benchmark_distinguishes_clean_blanks_and_crossed_out_entries():
    labels = [label(status='blank', literal=''), label(row=1, status='struck-out-blank', literal=''),
              label(row=2, status='struck-out-blank', literal='')]
    predictions = [{'sheet': 'S01', 'row': row, 'field': 'in1', 'status': status}
                   for row, status in enumerate(('blank', 'unreadable-or-invalid', 'alignment-failed'))]
    counts = evaluate_cells(labels, predictions, 3)['counts']
    assert counts['correct_clean_blanks'] == 1
    assert counts['crossed_out_flagged_for_review'] == 1
    assert counts['crossed_out'] == 2


def test_only_fresh_acceptance_can_pass_and_single_pair_fields_must_stay_empty():
    prediction = {'sheet': 'S01', 'row': 0, 'field': 'in1', 'raw': '8:30A', 'suggestion': '8:30A'}
    assert not evaluate_cells([label()], [prediction], 1, acceptance_verified=True)['target_met']
    fresh = [label(split='acceptance')]
    assert not evaluate_cells(fresh, [prediction], 1)['target_met']
    assert evaluate_cells(fresh, [prediction], 1, acceptance_verified=True)['target_met']
    filled = prediction | {'value': '8:30A'}
    assert not evaluate_cells(fresh, [filled], 1, acceptance_verified=True)['target_met']


def test_acceptance_requires_a_frozen_source_and_disjoint_writers():
    from experiments.evaluate_real_forms import verify_acceptance

    prior = {'original_sha256': 'a' * 64, 'split': 'holdout', 'writer_id': 'first'}
    fresh = {'original_sha256': 'b' * 64, 'split': 'acceptance', 'writer_id': 'second',
             'cells': [{'row': row, 'field': field} for row in range(14) for field in ('in1', 'out1')]}
    run = {'variant': 'original', 'source_sha': 'c' * 40}
    reference = {'sheets': [prior]}
    manifest = {'sheets': [prior, fresh], 'acceptance_source_sha': run['source_sha']}
    verify_acceptance(manifest, reference, run)
    with pytest.raises(ValueError, match='frozen source'):
        verify_acceptance(manifest, reference, run | {'source_sha': 'd' * 40})
    with pytest.raises(ValueError, match='disjoint'):
        verify_acceptance(manifest | {'sheets': [prior, fresh | {'writer_id': 'first'}]}, reference, run)
    with pytest.raises(ValueError, match='Preserve the reference'):
        verify_acceptance(manifest | {'sheets': [fresh]}, reference, run)
