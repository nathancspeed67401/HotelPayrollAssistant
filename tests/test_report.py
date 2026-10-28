from app.core import Sheet, ShiftDay
from app.report import export_excel
import zipfile
import pytest


def test_xlsx(tmp_path):
    s = Sheet('scan.jpg#page1', 'sample-sha', 'Sample Employee', '2026-10-24', approved=True)
    s.days[3] = ShiftDay('12A','8A')
    s.reviewed_days=[True]*14
    path = tmp_path / 'test.xlsx'
    export_excel(str(path), [s])
    assert zipfile.is_zipfile(path)
    with zipfile.ZipFile(path) as z:
        assert b'PAYROLL SUMMARY' in z.read('xl/workbook.xml')


def test_refuses_unapproved(tmp_path):
    s=Sheet('x','sha','Person','2026-10-24')
    with pytest.raises(ValueError, match='Not reviewed'):
        export_excel(str(tmp_path/'a.xlsx'),[s])
