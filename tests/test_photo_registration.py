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


def test_unregistered_page_cannot_populate_guessed_fixed_boxes(tmp_path):
    from PIL import Image
    from app.ocr import scan_page
    page=Image.new('RGB',(958,1350),'white')
    path=tmp_path/'blank.png';page.save(path)
    sheet=scan_page(str(path),page)
    assert all(not getattr(day,k) for day in sheet.days for k in ('in1','out1','in2','out2'))
    assert any('aligned' in w for w in sheet.scan_warnings)
