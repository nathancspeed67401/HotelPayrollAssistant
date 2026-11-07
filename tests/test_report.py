from app.core import Sheet, ShiftDay
from app.report import export_excel
import zipfile
import pytest
from tests.helpers import approve_sheet


def test_xlsx(tmp_path):
    s = Sheet('scan.jpg#page1', 'sample-sha', 'Sample Employee', '2026-10-24', approved=True)
    s.days[3] = ShiftDay('12A','8A')
    s.reviewed_days=[True]*14
    approve_sheet(s,tmp_path)
    path = tmp_path / 'test.xlsx'
    export_excel(str(path), [s])
    assert zipfile.is_zipfile(path)
    with zipfile.ZipFile(path) as z:
        assert b'PAYROLL SUMMARY' in z.read('xl/workbook.xml')


def test_refuses_unapproved(tmp_path):
    s=Sheet('x','sha','Person','2026-10-24')
    with pytest.raises(ValueError, match='Not reviewed'):
        export_excel(str(tmp_path/'a.xlsx'),[s])


def test_workbook_retains_exact_minutes_in_rows_and_grand_total(tmp_path):
    from openpyxl import load_workbook

    sheets = []
    for name in ('Employee One', 'Employee Two'):
        sheet = Sheet('x', name, name, '2026-10-24')
        sheet.days[6] = ShiftDay('11:59P', '12A')
        sheet.days[7] = ShiftDay('12A', '12:01A')
        sheets.append(approve_sheet(sheet, tmp_path, name))
    path = tmp_path / 'minutes.xlsx'
    export_excel(str(path), sheets)
    with path.open('rb') as stream:
        workbook = load_workbook(stream, data_only=True)
        summary = workbook['PAYROLL SUMMARY']
        assert summary['B6'].value == pytest.approx(1 / 60)
        assert summary['C6'].value == pytest.approx(1 / 60)
        assert summary['D6'].value == pytest.approx(2 / 60)
        assert summary['D8'].value == pytest.approx(4 / 60)
        detail = workbook['TIME DETAILS']
        assert detail['I8'].value.date().isoformat() == '2026-10-30'
        assert detail['I9'].value.date().isoformat() == '2026-10-31'
        assert detail['H8'].value == pytest.approx(1 / 60)
        assert detail['H9'].value == pytest.approx(1 / 60)
