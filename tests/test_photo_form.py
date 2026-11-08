"""Regression tests for the actual one-in/out-per-day Comfort Suites photo form.

Fixtures are generated with no real worker names or payroll images.
"""
import pytest
from PIL import Image, ImageDraw
from app.core import Sheet
from app import photo_form


def test_old_form_not_overwritten_by_14_row_photo_layout():
    assert len(photo_form.ROW_BOUNDS) == 14
    assert len(photo_form.PUNCH_COLUMNS) == 2
    assert all(a < b for a, b in photo_form.ROW_BOUNDS)
    assert photo_form.ROW_BOUNDS[6][1] < photo_form.ROW_BOUNDS[7][0]


def test_paper_detection_handles_wood_background():
    photo = Image.new("RGB", (1000, 2200), (172, 139, 99))
    ImageDraw.Draw(photo).rectangle((0, 180, 999, 1770), fill=(215, 214, 214))
    left, top, right, bottom = photo_form._paper_box(photo)
    assert left == 0 and right == 1000
    assert abs(top - 180) < 25
    assert abs(bottom - 1770) < 25
    assert photo_form.normalized_page(photo).size == (1000, 1470)


def test_faint_pencil_detected_but_blank_ignored():
    empty = Image.new("RGB", (125, 40), (212, 212, 212))
    marked = empty.copy()
    draw = ImageDraw.Draw(marked)
    for x in (20, 40, 60, 80):
        draw.line((x, 10, x+3, 30), fill=(75, 75, 75), width=3)
    assert not photo_form._has_ink(empty)
    assert photo_form._has_ink(marked)


def test_printed_cell_perimeter_is_not_employee_handwriting():
    cell=Image.new('RGB',(125,48),(210,210,210))
    ImageDraw.Draw(cell).rectangle((0,0,124,47),outline=(60,60,60),width=4)
    assert not photo_form._has_ink(cell)


def test_faint_pencil_still_requires_review_on_dim_paper():
    empty = Image.new('L', (125, 48), 128)
    marked = empty.copy()
    draw = ImageDraw.Draw(marked)
    for x in (25, 50, 75):
        draw.line((x, 10, x + 3, 36), fill=113, width=3)
    assert not photo_form._has_ink(empty)
    assert photo_form._has_ink(marked)


def test_ambiguous_no_ampm_is_not_silently_added():
    from app.line_ocr import choose_clock,Reading
    result = choose_clock([Reading('06:45',.99,.98,'raw')])
    assert result.raw == '06:45' and not result.value
    assert result.status == 'needs-AM/PM-or-minutes'


def test_missing_minutes_do_not_turn_into_valid_hour():
    from app.line_ocr import choose_clock,Reading
    assert choose_clock([Reading('6A',.99,.98,'raw')]).value == ''


def test_strong_real_form_ocr_only_offers_a_suggestion(monkeypatch, tmp_path):
    from app.line_ocr import Reading
    from app.ocr import scan_page
    from app.review import mark_row_reviewed
    from app.smoke import single_pair_fixture
    from types import SimpleNamespace

    page, _ = single_pair_fixture()
    engine = SimpleNamespace(recognize=lambda cells, views: [
        [Reading('１１．００Ｐ．Ｍ．', .99, .98, 'raw')] for _ in cells])
    monkeypatch.setattr('app.line_ocr.get_recognizer', lambda: engine)
    source = tmp_path / 'fixture.png'
    page.save(source)
    sheet = scan_page(str(source), page)
    assert sheet.days[0].observations['in1']['proposal'] == '11:00P'
    assert sheet.days[0].observations['in1']['candidates'][0]['text'] == '11:00PM'
    assert not sheet.days[0].in1 and not sheet.days[0].out1
    with pytest.raises(ValueError, match='Writing needs a time'):
        mark_row_reviewed(sheet, 0)


def test_upside_down_form_rotates_for_ocr_and_archive(monkeypatch, tmp_path):
    from app.review import archive_page
    # Camera orientation can be wrong even after EXIF transpose. Distinguish
    # the page by an artificial red orientation pixel, never private photos.
    page = Image.new("RGB", (1000, 1470), "white")
    page.putpixel((999, 1469), (200, 0, 0))
    monkeypatch.setattr(photo_form, "_header_matches",
                        lambda im: im.getpixel((0, 0))[0] == 200)
    monkeypatch.setattr(photo_form, "_row_transform", lambda image: (1.0, 0))
    monkeypatch.setattr(photo_form, "_has_ink", lambda cell: False)
    monkeypatch.setattr("app.ocr._ocr_cell", lambda image, characters: "")
    assert photo_form.is_this_form(page)
    sheet = Sheet("photo.jpg", "upside-down-fixture")
    photo_form.scan_this_form(sheet, page)
    assert sheet.rotate_180_for_archive
    assert sheet.form_type == photo_form.FORM_ID
    archive_page(sheet, page, tmp_path)
    with Image.open(sheet.source.split("#")[0]) as archived:
        assert archived.getpixel((0, 0)) == (200, 0, 0)


def test_photo_recognition_uses_original_resolution_clock_cells(monkeypatch):
    import numpy as np
    from types import SimpleNamespace
    from app.line_ocr import Reading
    from app.smoke import single_pair_fixture

    page, rows = single_pair_fixture()
    photo = page.resize((2000, 2940), Image.Resampling.NEAREST)
    y = 2 * (rows[0][0] + 23)
    ImageDraw.Draw(photo).line((751, y, 751, y + 14), fill=(19, 62, 176))
    received = []

    def recognize(cells, views):
        received.extend(cells)
        return [[Reading('23:00', .99, .98, 'raw')] for _ in cells]

    monkeypatch.setattr('app.line_ocr.get_recognizer', lambda: SimpleNamespace(recognize=recognize))
    sheet = Sheet('fictional.png', 'fixture')
    assert photo_form.scan_this_form(sheet, photo)
    assert len(sheet.review_boxes) == 14
    assert received[0].width > 230 and received[0].height > 85
    pixels = np.asarray(received[0]).astype('int16')
    assert np.count_nonzero(pixels[:, :, 2] - pixels[:, :, 0] > 70) >= 8
    assert sheet.days[0].observations['in1']['proposal'] == '11:00P'
    assert all(not (day.in1 or day.out1 or day.in2 or day.out2) for day in sheet.days)


def test_orientation_flag_persists_through_session():
    original = Sheet("photo.jpg", "test-hash")
    original.form_type = photo_form.FORM_ID
    original.rotate_180_for_archive = True
    loaded = Sheet.from_dict(original.to_dict())
    assert loaded.rotate_180_for_archive is True
    assert loaded.form_type == photo_form.FORM_ID


@pytest.mark.parametrize('tall_header', [False, True])
def test_real_import_withholds_suggestions_for_crossed_out_clocks(tall_header, tmp_path):
    from PIL import ImageFont

    from app.ocr import scan_page
    from app.review import mark_row_reviewed
    from app.smoke import single_pair_fixture

    page, rows = single_pair_fixture(tall_header)
    draw = ImageDraw.Draw(page)
    if tall_header:
        strokes = {
            'faint': ((8, 19, 111, 19),),
            'dash': ((8, 23, 110, 23),),
            'shallow': ((8, 26, 111, 14),),
            'edge': ((7, 41, 111, 41),),
            'underline': ((7, 36, 111, 36),),
        }
        expected = ('10:23P', '6:45A')
    else:
        strokes = {
            'horizontal': ((8, 22, 108, 22),),
            'low': ((8, 28, 108, 28),),
            'diagonal': ((8, 39, 108, 9),),
            'cross': ((8, 39, 108, 9), (8, 9, 108, 39)),
            'underline': ((8, 40, 108, 40),),
        }
        expected = ('8:41A', '3:19P')
    scenarios = ('clean', 'blank', *strokes)
    for row, (top, _) in enumerate(rows):
        scenario = scenarios[row % 7]
        if tall_header:
            ink = (55, 57, 64) if row < 7 else (27, 52, 131)
            font = ImageFont.load_default(size=21 if row < 7 else 26)
            text_x, text_y = 21, 6
        else:
            ink = (25, 45, 140) if row < 7 else (55, 55, 55)
            font = ImageFont.load_default(size=25)
            text_x, text_y = 15, 8
        for left, text in zip((265, 390), expected, strict=True):
            draw.rectangle((left + 2, top + 2, left + 121, top + 43), fill='white')
            if scenario == 'blank':
                continue
            if scenario != 'dash':
                draw.text((left + text_x, top + text_y), text, font=font, fill=ink)
            for x1, y1, x2, y2 in strokes.get(scenario, ()):
                stroke = (174, 176, 181) if scenario == 'faint' else ink
                draw.line((left + x1, top + y1, left + x2, top + y2), fill=stroke, width=2)

    source = tmp_path / 'fictional-crossed-clocks.png'
    page.save(source)
    sheet = scan_page(str(source), page)

    assert len(sheet.review_boxes) == 14
    for row, day in enumerate(sheet.days):
        scenario = scenarios[row % 7]
        for field, time in zip(('in1', 'out1'), expected, strict=True):
            observation = day.observations[field]
            if scenario in ('clean', 'edge', 'underline'):
                assert observation['proposal'] == time
            elif scenario == 'blank':
                assert observation['status'] == 'blank'
            else:
                assert observation['status'] != 'blank'
                assert not observation['proposal']
        assert not (day.in1 or day.out1 or day.in2 or day.out2)

    assert sheet.days[2].observations['in1']['status'] == 'possible-strike-through'
    with pytest.raises(ValueError, match='Writing needs a time'):
        mark_row_reviewed(sheet, 2)


def test_real_import_withholds_short_strikes_that_bridge_clock_ink(tmp_path):
    from PIL import ImageFont

    from app.ocr import scan_page
    from app.review import mark_row_reviewed
    from app.smoke import single_pair_fixture

    page, rows = single_pair_fixture(tall_header=True)
    draw = ImageDraw.Draw(page)
    marks = (None, (7, 36, 111, 36), (7, 41, 111, 41), (19, 20, 91, 20),
             (8, 19, 111, 19), (8, 26, 111, 14), (8, 23, 110, 23))
    clocks = {'in1': '10:23P', 'out1': '6:45A'}
    for row, (top, _) in enumerate(rows):
        ink = (55, 57, 64) if row < 7 else (27, 52, 131)
        font = ImageFont.load_default(size=21 if row < 7 else 26)
        design = row % 7
        for left, time in zip((265, 390), clocks.values(), strict=True):
            draw.rectangle((left + 2, top + 2, left + 121, top + 43), fill='white')
            if design != 6:
                draw.text((left + 21, top + 6), time, font=font, fill=ink)
            if mark := marks[design]:
                x1, y1, x2, y2 = mark
                stroke = (174, 176, 181) if design == 4 else ink
                draw.line((left + x1, top + y1, left + x2, top + y2), fill=stroke, width=2)

    source = tmp_path / 'fictional-short-strikes.png'
    page.save(source)
    sheet = scan_page(str(source), page)

    assert len(sheet.review_boxes) == 14
    for row, field in ((3, 'in1'), (3, 'out1'), (10, 'in1'), (10, 'out1')):
        observation = sheet.days[row].observations[field]
        assert observation['status'] == 'possible-strike-through'
        assert not observation['proposal']

    for row in (0, 1, 2, 7, 8, 9):
        for field, time in clocks.items():
            assert sheet.days[row].observations[field]['proposal'] == time
    assert all(not (day.in1 or day.out1 or day.in2 or day.out2) for day in sheet.days)
    with pytest.raises(ValueError, match='Writing needs a time'):
        mark_row_reviewed(sheet, 3)


@pytest.mark.parametrize('alternate_available', [True, False])
def test_photo_import_keeps_only_review_text_when_primary_reader_fails(
        alternate_available, monkeypatch, tmp_path):
    from types import SimpleNamespace

    from PIL import ImageFont

    from app.line_ocr import LineOCRError, Reading
    from app.ocr import scan_page
    from app.review import mark_row_reviewed
    from app.smoke import single_pair_fixture

    page, rows = single_pair_fixture()
    top = rows[1][0]
    draw = ImageDraw.Draw(page)
    ink = (25, 45, 140)
    draw.text((280, top + 8), '8:41A', font=ImageFont.load_default(size=25), fill=ink)
    draw.line((273, top + 22, 373, top + 22), fill=ink, width=2)

    def missing_primary():
        raise LineOCRError('Primary reader missing')

    def alternate(cells):
        if not alternate_available:
            raise LineOCRError('Alternate reader missing')
        assert len(cells) == 3
        return [
            [Reading('23:00', .99, .98, 'clock-18'), Reading('2300', .99, .97, 'clock-23')],
            [Reading('07:00', .99, .98, 'clock-18'), Reading('07:50', .99, .98, 'clock-23')],
            [Reading('8:41A', .99, .98, 'clock-18'), Reading('8:41A', .99, .98, 'clock-23')],
        ]

    monkeypatch.setattr('app.line_ocr.get_recognizer', missing_primary)
    monkeypatch.setattr('app.clock_ocr.get_clock_recognizer', lambda: SimpleNamespace(recognize=alternate))
    source = tmp_path / 'fictional-reader-outage.png'
    page.save(source)
    sheet = scan_page(str(source), page)

    assert len(sheet.review_boxes) == 14
    agreed = sheet.days[0].observations['in1']
    if alternate_available:
        assert agreed['raw'] == '23:00'
        assert agreed['status'] == 'alternate-reader-review'
        assert agreed['transcription']['text'] == '23:00'
    else:
        assert not agreed['raw']
    assert not sheet.days[0].observations['out1']['raw']
    assert not sheet.days[1].observations['in1']['raw']
    assert sheet.days[1].observations['in1']['status'] != 'blank'
    assert sheet.days[2].observations['in1']['status'] == 'blank'
    assert all(not obs.get('proposal') for day in sheet.days for obs in day.observations.values())
    assert all(not (day.in1 or day.out1 or day.in2 or day.out2) for day in sheet.days)
    with pytest.raises(ValueError, match='Writing needs a time'):
        mark_row_reviewed(sheet, 0)


def test_faint_punches_require_an_explicit_review_decision(tmp_path):
    from PIL import ImageFont

    from app.ocr import scan_page
    from app.review import mark_row_reviewed
    from app.smoke import single_pair_fixture

    page, rows = single_pair_fixture()
    draw = ImageDraw.Draw(page)
    font = ImageFont.load_default(size=25)
    for row, (top, _) in enumerate(rows):
        for left, text in ((265, '8:41A'), (390, '3:19P')):
            draw.rectangle((left + 2, top + 2, left + 121, top + 44), fill='white')
            if row % 7 in (1, 2, 3, 4):
                tone = (249, 247, 245, 243)[row % 7 - 1]
                draw.text((left + 14, top + 6), text, font=font, fill=(tone,) * 3)
            elif row % 7 == 5:
                for x in (15, 35, 55, 75):
                    draw.line((left + x, top + 10, left + x, top + 12), fill=(248,) * 3)
            elif row % 7 == 6:
                draw.line((left + 5, top + 23, left + 110, top + 23), fill=(248,) * 3)

    path = tmp_path / 'fictional-faint-punches.png'
    page.save(path)
    sheet = scan_page(str(path), page)

    assert len(sheet.review_boxes) == 14
    for row, day in enumerate(sheet.days):
        expected = 'possible-faint-ink' if row % 7 in (1, 2, 3, 4) else 'blank'
        for field in ('in1', 'out1'):
            assert day.observations[field]['status'] == expected
            assert not day.observations[field].get('proposal')
            assert not day.recognized[field]
            assert not getattr(day, field)
    with pytest.raises(ValueError, match='Writing needs a time'):
        mark_row_reviewed(sheet, 1)
    assert not sheet.reviewed_days[1]
    sheet.days[1].blank_confirmed = ['in1', 'out1']
    mark_row_reviewed(sheet, 1)
    assert sheet.reviewed_days[1]


def test_overlapping_pen_colors_require_review(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from PIL import ImageFont

    from app.line_ocr import Reading
    from app.ocr import scan_page
    from app.review import mark_row_reviewed
    from app.smoke import single_pair_fixture

    engine = SimpleNamespace(recognize=lambda cells, views: [
        [Reading('9:41A', .99, .98, 'raw')] for _ in cells])
    monkeypatch.setattr('app.line_ocr.get_recognizer', lambda: engine)
    page, rows = single_pair_fixture()
    draw = ImageDraw.Draw(page)
    font = ImageFont.load_default(size=24)
    blue = (23, 42, 135)
    red = (150, 25, 35)

    for row, (top, _) in enumerate(rows):
        for left in (265, 390):
            draw.rectangle((left + 2, top + 2, left + 121, top + 43), fill='white')
            if row % 7 == 3:
                continue
            start = left + 16
            if row % 7 == 2:
                draw.text((start, top + 8), '9:41', font=font, fill=blue)
                draw.text((start + 63, top + 8), 'A', font=font, fill=red)
            else:
                text = '8:41A' if row % 7 == 1 else '9:41A'
                draw.text((start, top + 8), text, font=font, fill=blue)
            if row % 7 == 1:
                draw.text((start + 2, top + 7), '9', font=font, fill=red)
            if row % 7 == 4:
                draw.line((left + 9, top + 23, left + 109, top + 23), fill=blue, width=2)

    path = tmp_path / 'fictional-overwritten-punches.png'
    page.save(path)
    sheet = scan_page(str(path), page)
    assert len(sheet.review_boxes) == 14
    for row, day in enumerate(sheet.days):
        for field in ('in1', 'out1'):
            observation = day.observations[field]
            if row % 7 == 1:
                assert observation['status'] == 'possible-overwrite'
                assert not observation['proposal']
            elif row % 7 == 3:
                assert observation['status'] == 'blank'
            elif row % 7 == 4:
                assert observation['status'] == 'possible-strike-through'
                assert not observation['proposal']
            else:
                assert observation['proposal'] == '9:41A'
            assert not getattr(day, field)
    with pytest.raises(ValueError, match='Writing needs a time'):
        mark_row_reviewed(sheet, 1)


def test_two_stacked_clock_lines_require_explicit_review(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from PIL import ImageFont

    from app.line_ocr import Reading
    from app.ocr import scan_page
    from app.review import mark_row_reviewed
    from app.smoke import single_pair_fixture

    engine = SimpleNamespace(recognize=lambda cells, views: [
        [Reading('9:41A', .99, .98, 'raw')] for _ in cells])
    monkeypatch.setattr('app.line_ocr.get_recognizer', lambda: engine)
    page, rows = single_pair_fixture()
    draw = ImageDraw.Draw(page)
    small = ImageFont.load_default(size=16)
    normal = ImageFont.load_default(size=21)
    ink = (31, 39, 80)

    for row, (top, _) in enumerate(rows):
        kind = row % 7
        for left in (265, 390):
            draw.rectangle((left + 2, top + 2, left + 121, top + 43), fill='white')
            if kind == 3:
                continue
            if kind in (0, 1):
                first_ink = (156, 160, 178) if kind == 1 else ink
                draw.text((left + 17, top + 2), '8:17A', font=small, fill=first_ink)
                draw.text((left + 20, top + 21), '9:41A', font=normal, fill=ink)
            else:
                draw.text((left + 17, top + 10), '9:41A', font=normal, fill=ink)
            if kind in (4, 5):
                y = top + (35 if kind == 4 else 23)
                draw.line((left + 9, y, left + 109, y), fill=ink, width=2)

    path = tmp_path / 'fictional-stacked-clock-lines.png'
    page.save(path)
    sheet = scan_page(str(path), page)
    assert len(sheet.review_boxes) == 14
    for row, day in enumerate(sheet.days):
        for field in ('in1', 'out1'):
            observation = day.observations[field]
            if row % 7 in (0, 1):
                assert observation['status'] == 'possible-stacked-writing'
                assert not observation['proposal']
            elif row % 7 == 3:
                assert observation['status'] == 'blank'
            elif row % 7 == 5:
                assert observation['status'] == 'possible-strike-through'
                assert not observation['proposal']
            else:
                assert observation['proposal'] == '9:41A'
            assert not getattr(day, field)
    with pytest.raises(ValueError, match='Writing needs a time'):
        mark_row_reviewed(sheet, 0)


def test_pale_colored_clock_strokes_require_review(tmp_path):
    from PIL import ImageFont

    from app.ocr import scan_page
    from app.review import mark_row_reviewed
    from app.smoke import single_pair_fixture

    page, rows = single_pair_fixture()
    font = ImageFont.load_default(size=24)
    for row, (top, _) in enumerate(rows):
        for col, left in enumerate((265, 390)):
            kind = row % 7
            paper, pen = (
                ((232, 232, 232), (197, 249, 239)),
                ((225, 235, 244), (252, 220, 243)),
            )[col]
            tile = Image.new('RGB', (119, 42), paper)
            draw = ImageDraw.Draw(tile)
            if kind in (1, 2):
                draw.text((12, 7), '8:41A' if col == 0 else '3:19P', font=font, fill=pen)
            elif kind == 3:
                for x in range(tile.width):
                    shade = .75 + .25 * x / tile.width
                    draw.line((x, 0, x, tile.height), fill=tuple(round(c * shade) for c in paper))
            elif kind == 4:
                for x, y in ((13, 12), (30, 23), (42, 28), (69, 18), (88, 27)):
                    draw.line((x, y, x, y + 2), fill=pen)
            page.paste(tile, (left + 2, top + 2))

    path = tmp_path / 'fictional-pale-colored-punches.png'
    page.save(path)
    sheet = scan_page(str(path), page)
    assert len(sheet.review_boxes) == 14
    for row, day in enumerate(sheet.days):
        expected = 'possible-faint-ink' if row % 7 in (1, 2) else 'blank'
        for field in ('in1', 'out1'):
            assert day.observations[field]['status'] == expected
            assert not day.observations[field].get('proposal')
            assert not day.recognized[field]
            assert not getattr(day, field)
    with pytest.raises(ValueError, match='Writing needs a time'):
        mark_row_reviewed(sheet, 1)
