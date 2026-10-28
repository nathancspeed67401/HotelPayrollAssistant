"""Privacy and approval regression tests."""
from PIL import Image
from app.core import Sheet, ShiftDay
from app.review import archive_page, scan_available, review_issues
from app.report import export_excel
import pytest
import zipfile


def test_local_archive_survives_original_removal(tmp_path):
    original = tmp_path/'phone.jpg'
    Image.new('RGB',(958,1350),'white').save(original)
    s=Sheet(str(original)+'#page1','abc','Employee One','2026-10-24')
    archive_page(s, Image.open(original), tmp_path/'private')
    original.unlink()
    assert scan_available(s)
    assert s.source.startswith(str(tmp_path/'private'))
    with Image.open(s.source.split('#page')[0]) as image:
        assert image.size == (958,1350)


def test_all_fourteen_rows_must_be_reviewed(tmp_path):
    src=tmp_path/'scan.jpg'; src.write_bytes(b'fixture')
    s=Sheet(str(src)+'#page1','sha','Employee One','2026-10-24',approved=True)
    assert 'Only 0 of 14' in ' '.join(review_issues(s))
    with pytest.raises(ValueError,match='Not reviewed'):
        export_excel(str(tmp_path/'not-checked.xlsx'),[s])
    s.reviewed_days=[True]*14
    assert not review_issues(s)
    export_excel(str(tmp_path/'checked.xlsx'),[s])
    assert (tmp_path/'checked.xlsx').is_file()


def test_export_does_not_interpret_employee_as_excel_formula(tmp_path):
    s=Sheet('source.png#page1','sha', '=1+2','2026-10-24', approved=True,reviewed_days=[True]*14)
    out=tmp_path/'output.xlsx'; export_excel(str(out),[s])
    with zipfile.ZipFile(out) as z:
        # XLSX contains Excel formula totals, but input name must be a shared string, not a formula.
        assert b'=1+2' in z.read('xl/sharedStrings.xml')
        summary=z.read('xl/worksheets/sheet1.xml')
        assert b'<f>1+2</f>' not in summary


def test_missing_archived_image_blocks_review(tmp_path):
    s=Sheet(str(tmp_path/'missing.jpg')+'#page1','abc','Employee','2026-10-24',approved=True,reviewed_days=[True]*14)
    assert 'missing' in ' '.join(review_issues(s)).lower()
