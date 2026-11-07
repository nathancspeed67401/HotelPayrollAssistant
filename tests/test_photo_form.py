"""Regression tests for the actual one-in/out-per-day Comfort Suites photo form.

Fixtures are generated with no real worker names or payroll images.
"""
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


def test_ambiguous_no_ampm_is_not_silently_added():
    from app.line_ocr import choose_clock,Reading
    result = choose_clock([Reading('06:45',.99,.98,'raw')])
    assert result.raw == '06:45' and not result.value
    assert result.status == 'needs-AM/PM-or-minutes'


def test_missing_minutes_do_not_turn_into_valid_hour():
    from app.line_ocr import choose_clock,Reading
    assert choose_clock([Reading('6A',.99,.98,'raw')]).value == ''


def test_strong_real_form_ocr_only_offers_a_suggestion(monkeypatch):
    from app.line_ocr import Reading
    from app.review import mark_row_reviewed
    from app.smoke import single_pair_fixture
    from types import SimpleNamespace
    import pytest

    page, _ = single_pair_fixture()
    engine = SimpleNamespace(recognize=lambda cells, views: [
        [Reading('23:00', .99, .98, 'raw')] for _ in cells])
    monkeypatch.setattr('app.line_ocr.get_recognizer', lambda: engine)
    sheet = Sheet('fixture.png', 'fixture')
    photo_form.scan_this_form(sheet, page)
    assert sheet.days[0].observations['in1']['proposal'] == '11:00P'
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
