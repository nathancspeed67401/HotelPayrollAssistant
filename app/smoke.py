"""Exercise the installed desktop workflow using generated fictional data."""
from pathlib import Path
import tempfile
import time
import zipfile
from PIL import Image,ImageDraw,ImageFont


def single_pair_fixture(tall_header=False):
    page=Image.new('RGB',(1000,1470),'white')
    draw=ImageDraw.Draw(page)
    # Use the same portable built-in font on Windows and in packaged builds.
    font=ImageFont.load_default(size=18)
    draw.text((150,105),'BI-WEEKLY TIMESHEET',font=font,fill='black')
    draw.text((65,175),'COMFORT SUITES SALINA SOUTH',font=font,fill='black')
    draw.text((530,175),'715 WEST SCHILLING RD',font=font,fill='black')
    draw.text((65,230),'EMPLOYEE NAME: INSTALLATION TEST',font=font,fill='black')
    draw.text((530,230),'GENERAL MANAGER:    PAY PERIOD:',font=font,fill='black')
    columns=[65,140,265,390,515,625,740,900]
    rows=[]
    for header in (300,300+(65 if tall_header else 28)+7*48):
        header_height=65 if tall_header else 28
        for x,label in zip(columns,['DATE','DAY','TIME IN:','TIME OUT:','#ROOMS','TIME ALOTTED','TOTAL HOURS']):
            draw.text((x+5,header+4),label,font=font,fill='black')
        boundaries=[header+header_height+i*48 for i in range(8)]
        for y in [header]+boundaries:draw.line((65,y,900,y),fill='black',width=2)
        for i,y in enumerate(boundaries[:-1]):
            draw.text((70,y+5),['SAT.','SUN.','MON.','TUES.','WED.','THUR.','FRI.'][i],font=font,fill='black')
            rows.append((y,y+48))
    for x in columns:draw.line((x,300,x,rows[-1][1]),fill='black',width=2)
    draw.text((276,rows[0][0]+8),'23:00',font=ImageFont.load_default(size=25),fill='black')
    draw.text((401,rows[0][0]+8),'07:00',font=ImageFont.load_default(size=25),fill='black')
    return page,rows


def run_workflow_smoke():
    import app.ui as ui
    from .review import approval_current
    old_dir=ui.app_dir
    old_dialogs=(ui.messagebox.askyesno,ui.messagebox.showwarning,ui.messagebox.showerror,
                 ui.filedialog.asksaveasfilename, ui.filedialog.askopenfilenames)
    app=None
    with tempfile.TemporaryDirectory(prefix='payroll-workflow-') as directory:
        folder=Path(directory)
        ui.app_dir=lambda:folder/'session'
        ui.messagebox.askyesno=lambda title,*a,**k:title=='Confirm reviewed'
        warnings = []
        ui.messagebox.showwarning=lambda title, *_args, **_kwargs: warnings.append(title)
        ui.messagebox.showerror=lambda title, *_args, **_kwargs: warnings.append(title)
        output=folder/'payroll.xlsx'
        ui.filedialog.asksaveasfilename=lambda **kwargs:str(output)
        try:
            image,_=single_pair_fixture()
            photo=folder/'fictional.png';image.save(photo)
            pdf=folder/'fictional.pdf'
            image.save(pdf,'PDF',resolution=150)
            ui.filedialog.askopenfilenames = lambda **_kwargs: (str(photo), str(pdf), str(photo))
            app=ui.PayrollApp()
            app.add_files()
            deadline = time.monotonic() + 40
            while app.busy and time.monotonic() < deadline:
                app.update()
                time.sleep(.02)
            assert not app.busy, 'Timed out importing the photo and PDF'
            assert not warnings, warnings
            assert len(app.sheets) == 2
            assert 'Added 2 timesheet(s)' in app.status.get() and 'Skipped 1 duplicate' in app.status.get()
            for index, sheet in enumerate(app.sheets):
                assert sheet.form_type == 'comfort_suites_single_pair'
                assert len(sheet.review_boxes) == 14, 'Printed form registration failed'
                assert sheet.days[0].recognized.get('in1'), 'No real OCR transcription was produced'
                assert not sheet.approved
                app.show_sheet(index)
                app.name_var.set(f'Installation Test {index + 1}')
                app.date_var.set('10/24/2026')
                for row in range(14):
                    app.tree.selection_set(str(row));app.select_day()
                    times=['11P','7A','',''] if row in (0,7) else ['','','','']
                    for variable,value in zip(app.punch_vars,times):variable.set(value)
                    for variable,value in zip(app.blank_vars,times):variable.set(not value)
                    app._blank_changed();app.save_day()
                app.approve()
                assert approval_current(sheet)
            app.export();assert zipfile.is_zipfile(output)
            with zipfile.ZipFile(output) as z:
                strings = z.read('xl/sharedStrings.xml')
                assert b'Installation Test 1' in strings and b'Installation Test 2' in strings
            app.destroy();app=None
            app=ui.PayrollApp();app.update()
            assert len(app.sheets)==2 and all(approval_current(sheet) for sheet in app.sheets)
            app.tree.selection_set('0');app.select_day();app.punch_vars[1].set('8A')
            assert not app.sheets[0].approved
            before=output.read_bytes();app.export();assert output.read_bytes()==before
        finally:
            if app is not None:app.destroy()
            ui.app_dir=old_dir
            (ui.messagebox.askyesno,ui.messagebox.showwarning,ui.messagebox.showerror,
             ui.filedialog.asksaveasfilename, ui.filedialog.askopenfilenames)=old_dialogs
    return 0
