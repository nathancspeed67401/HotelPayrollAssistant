"""Excel output for KC. Contains no photos and no hourly pay rates."""
from datetime import datetime, timedelta
from pathlib import Path
import xlsxwriter
from .core import Sheet, calculate_day_minutes, summarize_minutes, validate_sheet, DAYS, fully_reviewed
from .review import review_issues, approval_current
import unicodedata
import tempfile
import os


def export_excel(path: str, sheets: list[Sheet]) -> None:
    if not sheets:
        raise ValueError("No timesheets to export")
    for s in sheets:
        if s.approved is not True or not fully_reviewed(s.reviewed_days):
            raise ValueError(f"Not reviewed and approved: {s.employee or Path(s.source).name}")
        bad = validate_sheet(s)
        if bad:
            raise ValueError(f"Errors for {s.employee}:\n" + "\n".join(bad))
        issues = review_issues(s)
        if issues or not approval_current(s):
            raise ValueError(f'Not reviewed and approved for current entries: {s.employee}\n'+'\n'.join(issues))
    seen = set()
    for s in sheets:
        key = (' '.join(unicodedata.normalize('NFKC',s.employee).casefold().split()), s.period_start)
        if key in seen:
            raise ValueError(f"Duplicate employee/pay period: {s.employee}")
        seen.add(key)
    if len({s.archived_hash for s in sheets}) != len(sheets):
        raise ValueError('Duplicate timesheet image in payroll')
    periods = {s.period_start for s in sheets}
    if len(periods) != 1:
        raise ValueError("All employees must have the same two-week pay period")
    first = datetime.strptime(next(iter(periods)), "%Y-%m-%d").date()
    destination = Path(path)
    handle = tempfile.NamedTemporaryFile(dir=destination.parent,suffix='.xlsx',delete=False)
    temporary = Path(handle.name)
    handle.close()
    try:
        _write_workbook(str(temporary),sheets,first)
        with temporary.open('r+b') as stream:
            os.fsync(stream.fileno())
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _write_workbook(path, sheets, first):
    workbook = xlsxwriter.Workbook(path,{'strings_to_formulas':False,'strings_to_urls':False})
    workbook.set_properties({"title": "Hotel payroll - review-approved summary", "comments": "Time assignments follow paper-timesheet labels. Overtime requires employer workweek verification."})
    navy = '#152B45'
    header = workbook.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': navy, 'align':'center', 'valign':'vcenter', 'border':1})
    title = workbook.add_format({'bold': True, 'font_color': navy, 'font_size':16})
    text = workbook.add_format({'border':1})
    number = workbook.add_format({'border':1, 'num_format':'0.00'})
    small = workbook.add_format({'font_color':'#4B5563','italic':True,'text_wrap':True,'valign':'top'})
    datefmt = workbook.add_format({'num_format':'mmm d, yyyy','border':1})
    summary = workbook.add_worksheet('PAYROLL SUMMARY')
    summary.hide_gridlines(2)
    summary.freeze_panes(5, 1)
    summary.set_landscape()
    summary.fit_to_pages(1, 1)
    summary.set_margins(.35, .35, .45, .45)
    summary.set_column('A:A', 26)
    summary.set_column('B:F', 17)
    summary.set_column('G:G', 22)
    summary.merge_range('A1:G1', 'PAYROLL SUMMARY - APPROVED ENTRIES', title)
    summary.merge_range('A2:G2', f"Period: {first.strftime('%b %d, %Y')} - {(first + timedelta(days=13)).strftime('%b %d, %Y')}", small)
    summary.merge_range('A3:G3', 'IMPORTANT: Overtime columns are preliminary until the hotel confirms its fixed workweek boundary; paper-day assignment is not necessarily the legal workweek.', small)
    summary.set_row(2, 33)
    headers = ['Employee','Week 1 hours','Week 2 hours','All hours','Regular (est.)','OT (est.)','Approved']
    for col, val in enumerate(headers):
        summary.write(4, col, val, header)
    ordered = sorted(sheets, key=lambda sheet: sheet.employee.lower())
    totals = [summarize_minutes(sheet) for sheet in ordered]
    fields = ('week1', 'week2', 'total', 'regular', 'overtime')
    for r, (s, sums) in enumerate(zip(ordered, totals), start=5):
        summary.write_string(r, 0, s.employee, text)
        for c, field in enumerate(fields, start=1):
            summary.write_number(r, c, sums[field] / 60, number)
        summary.write(r, 6, 'YES', text)
    total_row = len(sheets) + 5
    summary.write(total_row, 0, 'TOTAL', header)
    for c, field in enumerate(fields, start=1):
        cc = chr(65 + c)
        summary.write_formula(total_row, c, f'=SUM({cc}6:{cc}{total_row})', number,
                              sum(sums[field] for sums in totals) / 60)
    summary.write_blank(total_row, 6, None, header)
    summary.autofilter(4, 0, total_row-1, 6)

    detail = workbook.add_worksheet('TIME DETAILS')
    detail.hide_gridlines(2)
    detail.freeze_panes(1, 3)
    detail.set_column('A:A', 24)
    detail.set_column('B:B', 14)
    detail.set_column('C:C', 15)
    detail.set_column('D:G', 14)
    detail.set_column('H:H', 14)
    detail.set_column('I:I', 22)
    for c, val in enumerate(['Employee','Week','Paper day','In 1','Out 1','In 2','Out 2','Hours','Date on paper']):
        detail.write(0, c, val, header)
    r = 1
    for s in ordered:
        for i, day in enumerate(s.days):
            detail.write_string(r,0,s.employee,text)
            detail.write_number(r,1,i//7+1,number)
            detail.write(r,2,DAYS[i%7],text)
            for c, key in enumerate(('in1','out1','in2','out2'),3):
                detail.write_string(r,c,getattr(day,key),text)
            minutes, _ = calculate_day_minutes(day)
            detail.write_number(r,7,minutes / 60,number)
            detail.write_datetime(r,8,datetime.combine(first+timedelta(days=i),datetime.min.time()),datefmt)
            r += 1
    detail.autofilter(0,0,r-1,8)
    info = workbook.add_worksheet('READ ME')
    info.set_column('A:A', 115)
    info.write(0,0,'SOURCE: employee-signed paper timesheets. Every image was reviewed manually before this export.',small)
    info.write(2,0,'Each shift is recorded under the DAY WRITTEN ON THE PAPER FORM, including overnight shifts.',small)
    info.write(4,0,'Do not send employee photos or handwritten signatures to Kansas City unless specifically required.',small)
    info.write(6,0,'Overtime shown is an estimate: over 40 hours in each Saturday-Friday form week. It MUST be verified against the employer-defined fixed 168-hour workweek and correct actual timing.',small)
    info.write(8,0,'Records and original signed timesheets should be retained following company policy and applicable labor laws.',small)
    info.write(10,0,'Hours are elapsed punch minutes shown as decimal hours. Displayed values round to two decimals. Totals use the original minutes. Meal deductions and payroll rounding policies are not applied.',small)
    workbook.close()
