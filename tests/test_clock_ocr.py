from PIL import Image
import pytest

from app.clock_ocr import corroborate_clock, get_clock_recognizer
from app.line_ocr import Reading, choose_clock


def reading(text, source, minimum=.93):
    return Reading(text, .96, minimum, source)


def test_second_reader_checks_a_complete_clock_from_another_view():
    primary = [reading('8:1ZP', 'raw'), reading('8:12PM', 'gray')]
    original = choose_clock(primary)
    assert original.value == ''
    checked, preferred = corroborate_clock(primary, [reading('812P', 'clock-18')], original)
    assert checked.value == '8:12P'
    assert checked.status == 'suggestion'
    assert preferred.text == '812P'


@pytest.mark.parametrize(('primary_text', 'secondary_text'), [
    ('8:12', '8:12P'),
    ('8P', '8:00P'),
    ('8:12AM', '8:12P'),
    ('8:10P', '8:12P'),
])
def test_second_reader_cannot_supply_unseen_or_conflicting_punch_information(primary_text, secondary_text):
    primary = [reading(primary_text, 'gray')]
    original = choose_clock(primary)
    checked, _ = corroborate_clock(primary, [reading(secondary_text, 'clock-18')], original)
    assert original.value == ''
    assert checked.value == ''


def test_uncorroborated_reading_is_only_a_transcription():
    primary = [reading('8:1ZP', 'raw')]
    original = choose_clock(primary)
    checked, preferred = corroborate_clock(primary, [reading('8:12P', 'clock-18')], original)
    assert checked.value == ''
    assert checked.status == 'uncertain-reading'
    assert preferred.text == '8:12P'


def test_uncorroborated_reading_requires_stronger_evidence_to_be_displayed():
    primary = [reading('8:1ZP', 'raw')]
    original = choose_clock(primary)
    secondary = [reading('8:12P', 'clock-18', .89)]
    assert corroborate_clock(primary, secondary, original) == (original, None)


def test_two_plausible_second_reader_results_keep_the_original_review_state():
    primary = [reading('8:12P', 'gray')]
    original = choose_clock(primary)
    secondary = [reading('8:12P', 'clock-18'), reading('8:17P', 'clock-23', .49)]
    assert corroborate_clock(primary, secondary, original) == (original, None)


def test_bundled_second_reader_runs_offline():
    readings = get_clock_recognizer().recognize([Image.new('RGB', (120, 45), 'white')])
    assert len(readings) == 1
    assert [r.source for r in readings[0]] == ['clock-18', 'clock-23']
    assert all(r.text == '' or r.text == '?' for r in readings[0])


@pytest.mark.parametrize(('first', 'second', 'expected'), [
    ('8P', '8:00P', None),
    ('8:00', '8:00P', None),
    ('8P', '8PM', '8P'),
    ('8:00', '800', '8:00'),
    ('8:00P', '8:00A', None),
])
def test_outage_transcription_preserves_written_information(first, second, expected):
    from app.clock_ocr import review_transcription

    reads = [reading(first, 'clock-18', .98), reading(second, 'clock-23', .97)]
    result = review_transcription(reads)
    assert (result.text if result else None) == expected
    assert review_transcription([reads[0], reads[0]]) is None
    assert review_transcription([reads[0], reading(second, 'clock-23', .95)]) is None
