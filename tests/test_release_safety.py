import pytest
from app.core import Sheet, ShiftDay, calculate_day
from app.report import export_excel
from app.review import review_issues

@pytest.mark.parametrize('flags', [[], [True], [True]*15, ['yes']*14, [1]*14])
def test_export_rejects_malformed_review(tmp_path, flags):
    sheet = Sheet('scan.png#page1', 'hash', 'Person', '2026-10-24',
                  approved=True, reviewed_days=flags)
    with pytest.raises(ValueError, match='reviewed'):
        export_excel(str(tmp_path/'payroll.xlsx'), [sheet])

@pytest.mark.parametrize('day', [ShiftDay('8A','4P','12P','6P'),
                              ShiftDay('11P','3A','2A','5A')])
def test_overlapping_split_shifts_are_rejected(day):
    hours, errors = calculate_day(day)
    assert hours is None
    assert 'overlap' in ' '.join(errors).lower()

def test_split_shift_with_break():
    assert calculate_day(ShiftDay('8A','12P','1P','5P')) == (8.0, [])
