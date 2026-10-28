from app.core import ShiftDay, Sheet, normalize_time, calculate_day, summarize, validate_sheet


def test_times():
    assert normalize_time('12A') == ('00:00','')
    assert normalize_time('12P') == ('12:00','')
    assert normalize_time('230A') == ('02:30','')
    assert normalize_time('9:15P') == ('21:15','')
    assert normalize_time('00:00') == ('00:00','')
    assert normalize_time('9:15')[1]
    assert normalize_time('25:00')[1]


def test_over_night_assigned_paper_day():
    hours, errors = calculate_day(ShiftDay('11P', '7A'))
    assert hours == 8
    assert errors == []
    assert calculate_day(ShiftDay('12A','8A')) == (8, [])


def test_two_shifts():
    assert calculate_day(ShiftDay('8A', '12P', '1P', '5P')) == (8, [])
    assert calculate_day(ShiftDay('8A', ''))[0] is None
    assert calculate_day(ShiftDay('9A', '9A'))[0] is None
    assert calculate_day(ShiftDay('10A', '3A'))[0] is None


def test_no_biweekly_overtime_averaging():
    s = Sheet('test', 'sha', 'Test Employee', '2026-10-24')
    s.days[0] = ShiftDay('8A','8P')
    s.days[1] = ShiftDay('8A','8P')
    s.days[2] = ShiftDay('8A','8P')
    s.days[3] = ShiftDay('8A','4P')
    s.days[7] = ShiftDay('8A','4P')
    assert summarize(s) == {'week1': 44.0, 'week2': 8.0, 'total': 52.0, 'regular': 48.0, 'overtime': 4.0}
    assert validate_sheet(s) == []


def test_period_starts_saturday():
    s = Sheet('x','x','A','2026-10-25')
    assert 'Pay period must begin on Saturday' in validate_sheet(s)
