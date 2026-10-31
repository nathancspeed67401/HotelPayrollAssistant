from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.core import normalize_time
from app.line_ocr import (LineOCRError, LineRecognizer, Reading, choose_time,
                          decode_ctc, get_recognizer, prepare_view)
from app.model_assets import LINE_MODEL


def reading(text, source='raw', mean=.99, minimum=.98):
    return Reading(text, mean, minimum, source)


@pytest.mark.parametrize('text', ['124', '915', '930', '12', '9:15', '9:15A?', 'A'])
def test_ambiguous_or_incomplete_readings_do_not_become_punches(text):
    assert choose_time([reading(text), reading(text, 'blue')]).value == ''


def test_two_plausible_times_require_review_even_if_one_is_more_confident():
    result = choose_time([reading('12A'), reading('11A', 'blue', .86, .65)])
    assert result.value == '' and result.status == 'conflicting-readings'


def test_digit_model_disagreement_prevents_a_convincing_wrong_time():
    result = choose_time([reading('9A'), reading('9A', 'blue'),
                          reading('8A', 'digits-fixed', .65, .65)])
    assert result.value == '' and result.status == 'conflicting-readings'


def test_repeated_copy_of_one_weak_view_is_not_agreement():
    weak = reading('2:30A', mean=.85, minimum=.55)
    assert choose_time([weak, weak]).value == ''
    assert choose_time([weak, reading('230A', 'blue', .87, .57)]).value == '2:30A'


def test_strong_digit_suggestion_can_fill_when_line_model_abstains():
    assert choose_time([reading('8P', 'digits-grid', .95, .95)]).value == '8:00P'
    assert choose_time([reading('8P', 'digits-grid', .85, .85)]).value == ''


def test_midnight_is_preserved():
    assert normalize_time(choose_time([reading('12A')]).value) == ('00:00', '')


def test_ctc_keeps_repeats_separated_by_blank_and_computes_character_minimum():
    # 1, 1, blank, 1, A, A, blank must decode as 11A, not 1A or 111AA.
    matrix = np.full((7, 3), .01)
    for row, label in enumerate([1, 1, 0, 1, 2, 2, 0]):
        matrix[row, label] = .95 if row != 4 else .75
    result = decode_ctc(matrix, ['blank', '1', 'A'], 'raw')
    assert result.text == '11A' and result.minimum == .75
    assert choose_time([result, reading('11A', 'blue', .90, .75)]).value == '11:00A'


def test_model_dictionary_mismatch_is_an_explicit_failure():
    with pytest.raises(LineOCRError, match='dictionary'):
        decode_ctc(np.ones((3, 7)), ['blank', 'A'], 'raw')


def test_blue_cleanup_keeps_time_and_colon_but_removes_tiny_boundary_fragment():
    image = Image.new('RGB', (100, 40), 'white')
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 15, 32), fill=(20, 35, 150))
    draw.rectangle((25, 16, 27, 18), fill=(20, 35, 150))
    draw.rectangle((25, 25, 27, 27), fill=(20, 35, 150))
    draw.point((70, 0), fill=(20, 35, 150))
    clean = prepare_view(image, 'clean')
    assert (clean[:, :, 0] < 128).sum() == 6*23+18
    assert clean.shape[1] < 40


def test_missing_and_tampered_weights_fail_before_engine_startup(tmp_path):
    with pytest.raises(LineOCRError, match='missing'):
        LineRecognizer(tmp_path/'absent.onnx')
    invalid = tmp_path/'invalid.onnx'
    invalid.write_bytes(b'not the pinned public model')
    with pytest.raises(LineOCRError, match='integrity'):
        LineRecognizer(invalid)


@pytest.mark.skipif(not LINE_MODEL.is_file(), reason='Run scripts/fetch_ocr_model.py for model integration')
def test_bundled_model_reads_a_real_image_through_the_actual_graph():
    image = Image.new('RGB', (210, 55), 'white')
    ImageDraw.Draw(image).text((8, 8), '12:30A', font=ImageFont.load_default(size=32),
                               fill=(24, 42, 145))
    readings = get_recognizer().recognize([image])
    assert len(readings) == 1 and len(readings[0]) == 4
    assert normalize_time(choose_time(readings[0]).value) == ('00:30', '')


@pytest.mark.skipif(not LINE_MODEL.is_file(), reason='Run scripts/fetch_ocr_model.py for model integration')
def test_import_reads_varied_times_and_keeps_ambiguous_punch_unreviewed():
    import json
    from app.core import TIME_FIELDS
    from app.ocr import scan_page
    base = Path(__file__).resolve().parents[1]/'test_samples'
    ground = json.loads((base/'ground_truth.json').read_text())
    for filename in ('06_MultipleFonts.png', '08_AmbiguousTime.png'):
        case = next(c for c in ground if c['file'] == filename)
        with Image.open(base/filename) as image:
            sheet = scan_page(str(base/filename), image)
        assert sheet.approved is False and sheet.reviewed_days == [False]*14
        for row, day in enumerate(case['punches']):
            for field in TIME_FIELDS:
                expected, error = normalize_time(day[field])
                got = getattr(sheet.days[row], field)
                if error:
                    assert got == ''
                    assert any(w.startswith(f'Week {row//7+1} ') and field in w
                               for w in sheet.scan_warnings)
                else:
                    assert normalize_time(got) == (expected, '')
