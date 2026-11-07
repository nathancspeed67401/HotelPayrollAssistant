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


def test_unregistered_page_cannot_populate_guessed_fixed_boxes(tmp_path):
    from PIL import Image
    from app.ocr import scan_page
    page=Image.new('RGB',(958,1350),'white')
    path=tmp_path/'blank.png';page.save(path)
    sheet=scan_page(str(path),page)
    assert all(not getattr(day,k) for day in sheet.days for k in ('in1','out1','in2','out2'))
    assert any('aligned' in w for w in sheet.scan_warnings)
