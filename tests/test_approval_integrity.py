import json
import pytest
from app.core import Sheet,ShiftDay,save_session,load_session,calculate_day
from app.report import export_excel
from app.review import mark_row_reviewed,mark_sheet_approved,approval_current,review_issues
from app.storage import journal_import,recover_imports,SessionLock
from tests.helpers import approve_sheet


@pytest.mark.parametrize('mutation',['punch','employee','period','source','ocr'])
def test_current_values_are_required_even_if_boolean_approval_survives(tmp_path,mutation):
    sheet = approve_sheet(Sheet('x','hash','Person','2026-10-24'),tmp_path)
    if mutation == 'punch':sheet.days[0]=ShiftDay('8A','4P')
    elif mutation == 'employee':sheet.employee='Another Person'
    elif mutation == 'period':sheet.period_start='2026-11-07'
    elif mutation == 'source':sheet.source=sheet.source.replace('#page1','#page2')
    else:sheet.days[0].recognized['in1']='8A'
    assert not approval_current(sheet)
    with pytest.raises(ValueError,match='reviewed'):
        export_excel(str(tmp_path/'blocked.xlsx'),[sheet])


def test_missing_or_changed_evidence_blocks_direct_export(tmp_path):
    sheet=approve_sheet(Sheet('x','hash','Person','2026-10-24'),tmp_path)
    source=tmp_path/'sample.png'
    source.write_bytes(b'different image')
    with pytest.raises(ValueError,match='changed'):
        export_excel(str(tmp_path/'blocked.xlsx'),[sheet])
    source.unlink()
    with pytest.raises(ValueError,match='missing'):
        export_excel(str(tmp_path/'blocked.xlsx'),[sheet])


def test_written_unreadable_cell_cannot_be_cleared_as_an_ordinary_blank():
    sheet=Sheet('x','hash')
    sheet.days[0].observations['in1']={'status':'unreadable-or-invalid','raw':''}
    with pytest.raises(ValueError,match='Writing needs'):
        mark_row_reviewed(sheet,0)
    sheet.days[0].blank_confirmed=['in1']
    mark_row_reviewed(sheet,0)
    assert sheet.reviewed_days[0]


def test_atomic_export_keeps_existing_workbook_if_writing_fails(tmp_path,monkeypatch):
    import app.report as report
    sheet=approve_sheet(Sheet('x','hash','Person','2026-10-24'),tmp_path)
    output=tmp_path/'payroll.xlsx';output.write_bytes(b'previous approved workbook')
    def fail(path,*_args):
        from pathlib import Path
        Path(path).write_bytes(b'partial')
        raise OSError('disk unavailable')
    monkeypatch.setattr(report,'_write_workbook',fail)
    with pytest.raises(OSError):export_excel(str(output),[sheet])
    assert output.read_bytes()==b'previous approved workbook'
    assert sorted(p.name for p in tmp_path.glob('*.xlsx'))==['payroll.xlsx']


def test_session_backup_and_import_journal_survive_restart(tmp_path):
    path=tmp_path/'current_session.json'
    a=Sheet('a','a','Person','2026-10-24')
    save_session(str(path),[a]);a.employee='Corrected Person';save_session(str(path),[a])
    assert load_session(str(path.with_suffix('.json.bak')))[0].employee=='Person'
    pending=tmp_path/'pending';journal_import(a,pending)
    recovered=recover_imports(pending)
    assert len(recovered)==1 and recovered[0][1].employee=='Corrected Person'


def test_one_damaged_import_does_not_hide_other_recoverable_pages(tmp_path):
    journal_import(Sheet('a','a'),tmp_path)
    (tmp_path/'damaged.json').write_text('{incomplete')
    errors=[]
    assert len(recover_imports(tmp_path,errors))==1
    assert len(errors)==1 and (tmp_path/'damaged.json').exists()


def test_two_application_instances_cannot_overwrite_the_same_payroll(tmp_path):
    lock=SessionLock(tmp_path)
    try:
        with pytest.raises(RuntimeError,match='already open'):SessionLock(tmp_path)
    finally:lock.close()
    SessionLock(tmp_path).close()


def test_split_shift_cannot_jump_beyond_one_printed_day():
    hours,errors=calculate_day(ShiftDay('8P','4A','5P','9P'))
    assert hours is None and '24 hours' in ' '.join(errors)


def test_same_photo_under_two_employee_names_cannot_pay_twice(tmp_path):
    a=approve_sheet(Sheet('x','hash','Person One','2026-10-24'),tmp_path)
    b=Sheet.from_dict(a.to_dict());b.employee='Person Two';mark_sheet_approved(b)
    with pytest.raises(ValueError,match='Duplicate timesheet'):
        export_excel(str(tmp_path/'double.xlsx'),[a,b])


def test_forty_employee_workbook_has_real_cached_grand_totals(tmp_path):
    from openpyxl import load_workbook
    sheets=[]
    for i in range(40):
        sheet=Sheet('x',str(i),f'Employee {i:02}','2026-10-24')
        sheet.days[0]=ShiftDay('11P','7A')
        sheets.append(approve_sheet(sheet,tmp_path,f'employee-{i:02}'))
    path=tmp_path/'forty.xlsx';export_excel(str(path),sheets)
    workbook=load_workbook(path,data_only=True)
    assert workbook['PAYROLL SUMMARY']['D46'].value==320
    assert workbook['TIME DETAILS'].max_row==561
