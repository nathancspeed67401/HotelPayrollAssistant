import pytest
from app.smoke import single_pair_fixture
from app.photo_grid import find_photo_grid


@pytest.mark.parametrize('tall_header',[False,True])
def test_registered_crops_follow_all_fourteen_printed_day_rows(tall_header):
    page,expected=single_pair_fixture(tall_header)
    grid=find_photo_grid(page)
    assert grid is not None
    for row,(top,bottom) in enumerate(expected):
        quad=grid.cell_quad(row,0)
        assert abs(quad[0][1]-top)<5
        assert abs(quad[3][1]-bottom)<5
        assert abs(quad[0][0]-265)<5
        assert abs(quad[1][0]-390)<5


def test_short_printed_headers_can_be_read_in_isolation(monkeypatch):
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw

    page, rows = single_pair_fixture()
    draw = ImageDraw.Draw(page)
    marks = {}
    for row, (top, bottom) in enumerate(rows):
        for col, left in enumerate((265, 390)):
            x, y = left + 7, (top + bottom) // 2
            color = (25 + row * 12, 40 + col * 65, 220)
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
            marks[row, col] = color
    source = np.float32([[0, 0], [999, 0], [999, 1469], [0, 1469]])
    corners = np.float32([[26, 15], [983, 0], [999, 1451], [0, 1469]])
    warped = Image.fromarray(cv2.warpPerspective(np.asarray(page),
        cv2.getPerspectiveTransform(source, corners), page.size, borderValue=(255, 255, 255)))
    monkeypatch.setattr('app.photo_grid._header_rows', lambda _page: [])
    grid = find_photo_grid(warped)
    assert grid is not None and len(grid.row_bounds) == 14
    for (row, col), color in marks.items():
        crop = np.asarray(grid.crop_cell(warped, row, col), dtype='int16')
        assert (np.max(np.abs(crop - color), axis=2) < 12).sum() >= 18, (row, col)


def test_short_header_geometry_without_printed_clock_labels_is_rejected(monkeypatch):
    from PIL import ImageDraw

    page, rows = single_pair_fixture()
    draw = ImageDraw.Draw(page)
    for top in (rows[0][0], rows[7][0]):
        for left, right in ((265, 390), (390, 515)):
            draw.rectangle((left + 2, top - 26, right - 2, top - 2), fill='white')
    monkeypatch.setattr('app.photo_grid._header_rows', lambda _page: [])
    assert find_photo_grid(page) is None


def test_tall_headers_with_unreadable_page_text_use_printed_weekdays(monkeypatch):
    page, rows = single_pair_fixture(tall_header=True)
    monkeypatch.setattr('app.photo_grid._header_rows', lambda _page: [])
    grid = find_photo_grid(page)
    assert grid is not None
    for row, (top, bottom) in enumerate(rows):
        for col, left in enumerate((265, 390)):
            upper_left, _, _, lower_left = grid.cell_quad(row, col)
            assert abs(upper_left[0] - left) < 5
            assert abs(upper_left[1] - top) < 5
            assert abs(lower_left[1] - bottom) < 5


def test_missing_printed_day_boundary_cannot_be_interpolated():
    from PIL import ImageDraw

    page, rows = single_pair_fixture()
    _, missing_rule = rows[2]
    ImageDraw.Draw(page).rectangle((65, missing_rule - 2, 900, missing_rule + 2), fill='white')
    assert find_photo_grid(page) is None


def test_clock_separator_must_be_visible_in_both_weeks():
    from PIL import ImageDraw

    page, rows = single_pair_fixture()
    draw = ImageDraw.Draw(page)
    for top, bottom in rows[7:]:
        draw.rectangle((387, top + 3, 394, bottom - 3), fill='white')
    assert find_photo_grid(page) is None


def test_out_of_order_printed_weekdays_cannot_register():
    from PIL import ImageDraw, ImageFont

    page, rows = single_pair_fixture()
    draw = ImageDraw.Draw(page)
    top, bottom = rows[7]
    draw.rectangle((67, top + 2, 130, bottom - 2), fill='white')
    draw.text((70, top + 5), 'FRI.', fill='black', font=ImageFont.load_default(size=18))
    assert find_photo_grid(page) is None


def test_import_identifies_upside_down_form_from_grid_when_page_title_is_unreadable(monkeypatch, tmp_path):
    from app.ocr import scan_page

    page, _ = single_pair_fixture()
    page = page.rotate(180)
    source = tmp_path / 'fictional.png'
    page.save(source)
    monkeypatch.setattr('app.photo_form._header_matches', lambda _page: False)
    sheet = scan_page(str(source), page)
    assert sheet.form_type == 'comfort_suites_single_pair'
    assert sheet.archive_rotation == 180
    assert len(sheet.review_boxes) == 14
    assert all(not day.in1 and not day.out1 for day in sheet.days)


def test_unregistered_page_cannot_populate_guessed_fixed_boxes(tmp_path):
    from PIL import Image
    from app.ocr import scan_page
    page=Image.new('RGB',(958,1350),'white')
    path=tmp_path/'blank.png';page.save(path)
    sheet=scan_page(str(path),page)
    assert all(not getattr(day,k) for day in sheet.days for k in ('in1','out1','in2','out2'))
    assert any('aligned' in w for w in sheet.scan_warnings)


def test_verified_two_pair_import_skips_single_pair_registration(monkeypatch):
    from pathlib import Path
    from app.ocr import load_pages, scan_page

    def unexpected_registration(*args):
        pytest.fail('A verified legacy form should bypass single-pair registration')

    monkeypatch.setattr('app.photo_form.scan_this_form', unexpected_registration)
    source = Path(__file__).resolve().parents[1] / 'test_samples' / '03_SplitShifts.png'
    sheet = scan_page(str(source), load_pages(str(source))[0])
    day = sheet.days[1]
    assert len(sheet.review_boxes) == 14
    assert (day.in1, day.out1, day.in2, day.out2) == ('8:00A', '12:00P', '1:00P', '5:00P')


def test_legacy_geometry_with_one_pair_of_headings_cannot_prefill(tmp_path):
    from pathlib import Path
    from PIL import ImageDraw
    from app.core import TIME_FIELDS
    from app.form_geometry import find_form_grid
    from app.ocr import load_pages, scan_page

    legacy = Path(__file__).resolve().parents[1] / 'test_samples' / '03_SplitShifts.png'
    page = load_pages(str(legacy))[0]
    draw = ImageDraw.Draw(page)
    # Retain the grid and the clock ink. Erase the second pair of printed
    # headings only in week two, so the first week alone cannot select legacy.
    for left, right in ((480, 605), (609, 743)):
        draw.rectangle((left, 642, right, 671), fill=(251, 251, 248))
    assert find_form_grid(page) is not None
    source = tmp_path / 'unverified.png'
    page.save(source)
    sheet = scan_page(str(source), page)
    assert not sheet.review_boxes
    assert all(not getattr(day, field) for day in sheet.days for field in TIME_FIELDS)
