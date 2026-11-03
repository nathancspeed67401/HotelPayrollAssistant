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


def test_ambiguous_no_ampm_is_not_silently_added(monkeypatch):
    page = Image.new("RGB", (1000, 1470), "white")
    monkeypatch.setattr(photo_form, "normalized_page", lambda image: page)
    monkeypatch.setattr(photo_form, "_row_transform", lambda page: (1.0, 0))
    monkeypatch.setattr(photo_form, "_has_ink", lambda cell: True)
    monkeypatch.setattr(photo_form, "_time_candidate", lambda cell: "6:45")
    monkeypatch.setattr("app.ocr._ocr_cell", lambda image, characters: "JaneDoe")
    sheet = Sheet("example.png", "hash")
    photo_form.scan_this_form(sheet, page)
    assert sheet.form_type == photo_form.FORM_ID
    assert sheet.days[0].recognized["in1"] == "6:45"
    assert sheet.days[0].in1 == "" and sheet.days[0].out1 == ""
    assert len(sheet.scan_warnings) > 2
    assert sheet.reviewed_days == [False]*14


def test_missing_minutes_do_not_turn_into_valid_hour(monkeypatch):
    page = Image.new("RGB", (1000, 1470), "white")
    monkeypatch.setattr(photo_form, "normalized_page", lambda image: page)
    monkeypatch.setattr(photo_form, "_row_transform", lambda page: (1.0, 0))
    monkeypatch.setattr(photo_form, "_has_ink", lambda cell: True)
    monkeypatch.setattr(photo_form, "_time_candidate", lambda cell: "6A")
    monkeypatch.setattr("app.ocr._ocr_cell", lambda image, characters: "JaneDoe")
    sheet = Sheet("example.png", "hash")
    photo_form.scan_this_form(sheet, page)
    assert sheet.days[0].recognized["in1"] == "6A"
    assert sheet.days[0].in1 == ""
