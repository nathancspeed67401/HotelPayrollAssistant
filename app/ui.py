"""Simple photo-to-reviewed-payroll desktop workflow (Windows, fully offline)."""
from __future__ import annotations
import os
import sys
import threading
import queue
from datetime import date, timedelta, datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw, ImageOps
from .core import Sheet, DISPLAY, TIME_FIELDS, calculate_day, display_time, load_session, save_session, summarize, validate_sheet, fully_reviewed, row_fingerprint, valid_period
from .ocr import load_pages, scan_page, REF_W, REF_H, ROW_Y, COL_X
from .photo_form import FORM_ID, row_rect_original
from .report import export_excel
from .review import archive_page, scan_available, review_issues, mark_row_reviewed, mark_sheet_approved, approval_current, unresolved_empty_fields
from .storage import SessionLock, journal_import, recover_imports


def app_dir() -> Path:
    return Path(os.getenv('LOCALAPPDATA') or (Path.home() / '.local' / 'share')) / 'Hotel Payroll Assistant'


class PayrollApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        try:
            self._session_lock = SessionLock(app_dir())
        except RuntimeError as exc:
            self.withdraw()
            messagebox.showerror('Payroll is already open',str(exc))
            self.destroy()
            raise
        self.title('Hotel Payroll Assistant')
        width=min(1240,max(900,self.winfo_screenwidth()-40))
        height=min(800,max(600,self.winfo_screenheight()-80))
        self.geometry(f'{width}x{height}')
        self.minsize(min(1060,width),min(680,height))
        self.configure(bg='#eef3f8')
        self.sheets: list[Sheet] = []
        self.active_idx: int | None = None
        self.current_image: Image.Image | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.busy = False
        self._loading_punches = False
        self._loading_metadata = False
        self._import_queue = queue.Queue()
        self._cancel_import = threading.Event()
        self.recovery_issues=[]
        self._editing_day = None
        self._styles()
        self._layout()
        for variable in self.punch_vars:
            variable.trace_add('write', self._punch_changed)
        for variable in (self.name_var,self.date_var):
            variable.trace_add('write',self._metadata_changed)
        self._restore_session()
        self.protocol('WM_DELETE_WINDOW', self.close)

    def _styles(self) -> None:
        s = ttk.Style(self)
        if 'clam' in s.theme_names():
            s.theme_use('clam')
        s.configure('Title.TLabel', font=('Segoe UI', 19, 'bold'), foreground='#152b45', background='#eef3f8')
        s.configure('Sub.TLabel', font=('Segoe UI', 10), foreground='#566577', background='#eef3f8')
        s.configure('Head.TLabel', font=('Segoe UI', 11, 'bold'), foreground='#152b45', background='white')
        s.configure('Body.TLabel', font=('Segoe UI', 10), background='white')
        s.configure('Action.TButton', padding=(15, 12), font=('Segoe UI', 10, 'bold'))
        s.configure('TButton', font=('Segoe UI', 10), padding=(10, 6))
        s.configure('Treeview', rowheight=29, font=('Segoe UI', 10))
        s.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        s.map('Treeview', background=[('selected', '#dbeafe')], foreground=[('selected', '#172554')])

    def _layout(self) -> None:
        head = ttk.Frame(self, padding=(20, 14, 20, 8))
        head.pack(fill='x')
        ttk.Label(head, text='Hotel Payroll Assistant', style='Title.TLabel').pack(anchor='w')
        ttk.Label(head, text='1. Add timesheets    →    2. Review every punch    →    3. Export Excel for KC', style='Sub.TLabel').pack(anchor='w', pady=(3,0))
        toolbar = ttk.Frame(self, padding=(20, 5, 20, 8))
        toolbar.pack(fill='x')
        self.btn_add = ttk.Button(toolbar, text='①  Add Photos / PDFs', style='Action.TButton', command=self.add_files)
        self.btn_add.pack(side='left', padx=(0,8))
        self.btn_approve = ttk.Button(toolbar, text='②  Approve This Sheet', style='Action.TButton', command=self.approve)
        self.btn_approve.pack(side='left', padx=8)
        self.btn_export = ttk.Button(toolbar, text='③  Export Excel', style='Action.TButton', command=self.export)
        self.btn_export.pack(side='left', padx=8)
        ttk.Button(toolbar, text='New Pay Period', command=self.new_period).pack(side='right')
        self.status = tk.StringVar(value='Ready. Import timesheet photos or PDFs to begin.')
        ttk.Label(self, textvariable=self.status, style='Sub.TLabel', padding=(20, 0, 20, 8)).pack(anchor='w')
        outer = ttk.PanedWindow(self, orient='horizontal')
        outer.pack(fill='both', expand=True, padx=16, pady=(0,16))
        left = ttk.Frame(outer, padding=10)
        right = ttk.Frame(outer, padding=10)
        outer.add(left, weight=3)
        outer.add(right, weight=2)
        ttk.Label(left, text='Timesheets (select one)', style='Head.TLabel').pack(anchor='w', pady=(0,5))
        box = ttk.Frame(left)
        box.pack(fill='x')
        self.sheet_list = tk.Listbox(box, height=4, font=('Segoe UI', 11), activestyle='none', exportselection=False)
        scroll = ttk.Scrollbar(box, orient='vertical', command=self.sheet_list.yview)
        self.sheet_list.config(yscrollcommand=scroll.set)
        self.sheet_list.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self.sheet_list.bind('<<ListboxSelect>>', self.select_sheet)
        fields = ttk.Frame(left, padding=(0, 12, 0, 10))
        fields.pack(fill='x')
        ttk.Label(fields, text='Employee name', style='Head.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(fields, text='First Saturday of pay period (MM/DD/YYYY)', style='Head.TLabel').grid(row=0, column=1, sticky='w', padx=(12,0))
        self.name_var = tk.StringVar()
        self.date_var = tk.StringVar()
        ttk.Entry(fields, textvariable=self.name_var, width=26, font=('Segoe UI', 11)).grid(row=1, column=0, sticky='ew', pady=(3,0))
        ttk.Entry(fields, textvariable=self.date_var, width=30, font=('Segoe UI', 11)).grid(row=1, column=1, sticky='ew', padx=(12,0), pady=(3,0))
        fields.columnconfigure(0, weight=1)
        fields.columnconfigure(1, weight=1)
        ttk.Label(left, text='Select a day to review and edit its clock times', style='Head.TLabel').pack(anchor='w', pady=(4,5))
        table_frame = ttk.Frame(left)
        cols = ('day','in1','out1','in2','out2','hours','review')
        self.tree = ttk.Treeview(table_frame, columns=cols, show='headings', selectmode='browse', height=14)
        for name, label, width in [('day','DAY',97),('in1','IN 1',77),('out1','OUT 1',77),('in2','IN 2',77),('out2','OUT 2',77),('hours','HOURS',78),('review','CHECK',100)]:
            self.tree.heading(name, text=label)
            self.tree.column(name, width=width, minwidth=70, stretch=name in ('day','review'), anchor='center')
        self.tree.tag_configure('odd', background='#f6f9fe')
        self.tree.tag_configure('issue', background='#ffe3e3')
        self.tree.tag_configure('week', background='#e4f1ff')
        self.tree.bind('<<TreeviewSelect>>', self.select_day)
        self.tree.pack(fill='both', expand=True, side='left')
        tscroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.config(yscrollcommand=tscroll.set)
        tscroll.pack(side='right', fill='y')
        edit = ttk.LabelFrame(left, text='Edit selected day — enter 12A, 9:15P, 2:30A, etc.', padding=10)
        self.punch_vars = [tk.StringVar() for _ in range(4)]
        self.blank_vars = [tk.BooleanVar() for _ in range(4)]
        self.punch_entries = []
        self.punch_labels = []
        self.blank_checks = []
        for c, label in enumerate(['Time In', 'Time Out', 'Second In', 'Second Out']):
            heading=ttk.Label(edit,text=label,style='Body.TLabel')
            heading.grid(row=0,column=c,padx=4,sticky='w')
            self.punch_labels.append(heading)
            ent = ttk.Entry(edit, textvariable=self.punch_vars[c], width=13, font=('Segoe UI', 11))
            ent.grid(row=1, column=c, sticky='ew', padx=4, pady=4)
            ent.bind('<Return>', lambda _evt: self.save_day())
            self.punch_entries.append(ent)
            check=ttk.Checkbutton(edit,text='Blank / crossed out',variable=self.blank_vars[c],command=self._blank_changed)
            check.grid(row=2,column=c,sticky='w');self.blank_checks.append(check)
            edit.columnconfigure(c, weight=1)
        self.btn_save_day=ttk.Button(edit,text='✓ Checked: Save & Next',command=self.save_day)
        self.btn_save_day.grid(row=1,column=4,padx=(10,0),sticky='ew')
        self.totals = tk.StringVar(value='Week 1: —    Week 2: —    Total: —')
        ttk.Label(left,textvariable=self.totals,style='Head.TLabel').pack(side='bottom',anchor='w',pady=(5,0))
        edit.pack(side='bottom',fill='x',pady=(9,4))
        # Reserve the wage-entry controls first. The scrollable row table gets
        # the remaining height even on ordinary 768-pixel laptop displays.
        table_frame.pack(fill='both',expand=True)
        # Right: full original photo, zoomed selected row, and notes.
        ttk.Label(right, text='Original timesheet — compare every entry', style='Head.TLabel').pack(anchor='w', pady=(0,6))
        self.preview_frame = ttk.Frame(right)
        self.preview_frame.pack(fill='both', expand=True)
        self.img_label = ttk.Label(self.preview_frame, text='Import a photo to see it here', anchor='center')
        self.img_label.pack(fill='both', expand=True)
        self.img_label.bind('<Configure>', lambda _evt: self.update_preview())
        self.row_preview = ttk.Label(right, text='Selected row will appear here', anchor='center')
        self.row_preview.pack(fill='x', pady=(8,3))
        ttk.Button(right, text='🔎 Enlarge Handwriting', command=self.zoom_day).pack(anchor='e', pady=(1, 5))
        self.note_var = tk.StringVar(value='All OCR readings must be checked. Incorrect or incomplete entries are never approved automatically.')
        wrap = ttk.Label(right, textvariable=self.note_var, style='Body.TLabel', wraplength=430, justify='left')
        wrap.pack(fill='x', pady=(6,0))

    def _restore_session(self):
        path = app_dir() / 'current_session.json'
        recovered_backup=False
        try:
            if path.exists():
                try:
                    self.sheets = load_session(str(path))
                except (ValueError,KeyError,TypeError):
                    self.sheets = load_session(str(path.with_suffix('.json.bak')))
                    recovered_backup=True
                    self.status.set('Recovered the last saved backup. Recheck recent changes.')
            recovered = recover_imports(app_dir()/'pending-imports',self.recovery_issues)
            known = {s.source_hash for s in self.sheets}
            for journal,sheet in recovered:
                if sheet.source_hash not in known:
                    self.sheets.append(sheet);known.add(sheet.source_hash)
            for sheet in self.sheets:
                if recovered_backup:
                    sheet.approved=False
                    sheet.reviewed_days=[False]*14
                    sheet.row_fingerprints=['']*14
                if not approval_current(sheet) or review_issues(sheet):
                    sheet.approved = False
                if not isinstance(sheet.reviewed_days, list) or len(sheet.reviewed_days) != 14:
                    sheet.reviewed_days = [False]*14
                else:
                    sheet.reviewed_days = [v is True for v in sheet.reviewed_days]
                if len(sheet.row_fingerprints) != 14:
                    sheet.row_fingerprints = ['']*14
                for i in range(min(14,len(sheet.days))):
                    if sheet.row_fingerprints[i] != row_fingerprint(sheet,i):
                        sheet.reviewed_days[i] = False
            if recovered and self._save():
                for journal,_ in recovered:
                    journal.unlink(missing_ok=True)
            self.refresh_list()
            if self.sheets:
                self.sheet_list.selection_set(0)
                self.show_sheet(0)
                self.status.set('Recovered a previous backup. Recheck all rows before exporting.' if recovered_backup else 'Restored your last payroll session. Review each sheet before exporting.')
        except Exception as e:
            self.recovery_issues.append(f'Could not restore previous payroll: {e}')
            if path.is_file():
                from .core import _atomic_write
                preserved=path.with_name(f'preserved-{datetime.now():%Y%m%d-%H%M%S-%f}.json')
                _atomic_write(preserved,path.read_bytes())
            self.status.set(f'Could not restore previous payroll session: {e}')

    def _save(self):
        try:
            save_session(str(app_dir() / 'current_session.json'), self.sheets)
            return True
        except Exception as e:
            messagebox.showwarning('Save warning', f'Could not save your progress: {e}')
            return False

    def refresh_list(self):
        selected = self.active_idx
        self.sheet_list.delete(0, 'end')
        for index,s in enumerate(self.sheets):
            marker = '✓ Approved' if s.approved else f'● {sum(s.reviewed_days)}/14 checked'
            self.sheet_list.insert('end',f'{marker}   {s.employee or f"Timesheet {index+1}"}   {s.period_start or "Enter payroll period"}')
        if selected is not None and selected < len(self.sheets):
            self.sheet_list.selection_set(selected)

    def add_files(self):
        if self.busy: return
        names = filedialog.askopenfilenames(title='Select timesheet photos or PDFs',
               filetypes=[('Photos and PDFs','*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.pdf'),('All files','*.*')])
        if not names: return
        self.busy = True
        self._cancel_import.clear()
        self.btn_add.config(state='disabled')
        self.btn_export.config(state='disabled')
        self.status.set(f'Reading {len(names)} file(s) locally. Please keep the app open.')
        def work():
            errors = []
            for name in names:
                if self._cancel_import.is_set():break
                try:
                    for page_num, im in enumerate(load_pages(name), 1):
                        if self._cancel_import.is_set():break
                        scanned = scan_page(name, im, page_num)
                        scanned = archive_page(scanned, im, app_dir() / 'scans')
                        journal = journal_import(scanned,app_dir()/'pending-imports')
                        self._import_queue.put(('sheet',scanned,journal))
                except Exception as e:
                    errors.append(f'{Path(name).name}: {e}')
            self._import_queue.put(('done',errors,None))
        threading.Thread(target=work, daemon=True).start()
        self.after(100,self._poll_import)

    def _poll_import(self):
        try:
            while True:
                kind,value,journal = self._import_queue.get_nowait()
                if kind == 'done':
                    self._complete_import([],value)
                    return
                self._accept_import([value])
                if self._save():journal.unlink(missing_ok=True)
        except queue.Empty:
            if self.busy:self.after(100,self._poll_import)

    def _complete_import(self, results: list[Sheet], errors: list[str]):
        self.busy = False
        self.btn_add.config(state='normal')
        self.btn_export.config(state='normal')
        added = self._accept_import(results)
        self._save()
        self.status.set(f'Added {added} sheet(s) in this step. {len(self.sheets)} in this payroll. Review all entries.')
        if errors:
            messagebox.showwarning('Some scans need attention', '\n'.join(errors[:10]))

    def _accept_import(self, results):
        self.capture_metadata()
        existing = {s.source_hash for s in self.sheets}
        images = {s.archived_hash for s in self.sheets if s.archived_hash}
        unique = []
        for sheet in results:
            if sheet.source_hash not in existing and (not sheet.archived_hash or sheet.archived_hash not in images):
                unique.append(sheet)
                existing.add(sheet.source_hash)
                if sheet.archived_hash:images.add(sheet.archived_hash)
        # The same pay-period date is shared by every employee; enter it once.
        shared_date = next((x.period_start for x in self.sheets if valid_period(x.period_start)), '')
        for item in unique:
            if shared_date and not item.period_start:
                item.period_start = shared_date
        self.sheets.extend(unique)
        self.refresh_list()
        if unique:
            if self.active_idx is None:
                pos = len(self.sheets)-len(unique)
                self.sheet_list.selection_clear(0,'end')
                self.sheet_list.selection_set(pos)
                self.show_sheet(pos)
        return len(unique)

    def _metadata_changed(self,*_args):
        if not self._loading_metadata:
            self.capture_metadata()

    def select_sheet(self, _event=None):
        sel = self.sheet_list.curselection()
        if sel:
            n = sel[0]
            if n != self.active_idx:
                self.capture_metadata()
                self.show_sheet(n)

    def capture_metadata(self):
        if self.active_idx is None: return
        s = self.sheets[self.active_idx]
        new_name = self.name_var.get().strip()
        new_date = self.date_var.get().strip()
        if '/' in new_date:
            try:
                new_date = datetime.strptime(new_date, '%m/%d/%Y').strftime('%Y-%m-%d')
            except ValueError:
                pass
        if (s.employee, s.period_start) != (new_name, new_date):
            old_period = s.period_start
            s.employee, s.period_start = new_name, new_date
            s.approved = False
            # The form uses one shared payroll period; entering it once updates blank sheets.
            try:
                valid_period = datetime.strptime(new_date,'%Y-%m-%d').weekday() == 5
            except ValueError:
                valid_period = False
            if valid_period:
                for other in self.sheets:
                    if not other.period_start:
                        other.period_start = new_date
                        other.approved = False
            self._save()
            self.refresh_list()

    def show_sheet(self, index: int):
        self._editing_day = None
        self.active_idx = index
        s = self.sheets[index]
        single=s.form_type == FORM_ID
        self.tree.config(displaycolumns=('day','in1','out1','hours','review') if single else ('day','in1','out1','in2','out2','hours','review'))
        for column in (2,3):
            for widget in (self.punch_entries[column],self.punch_labels[column],self.blank_checks[column]):
                if single:widget.grid_remove()
                else:widget.grid()
            self.punch_entries[column].master.columnconfigure(column,weight=0 if single else 1)
        for entry in self.punch_entries[2:]:
            entry.config(state='disabled' if s.form_type == FORM_ID else 'normal')
        self._loading_metadata = True
        self.name_var.set(s.employee)
        if not s.period_start:
            s.period_start = next((x.period_start for x in self.sheets if valid_period(x.period_start)), '')
        try:
            self.date_var.set(datetime.strptime(s.period_start, '%Y-%m-%d').strftime('%m/%d/%Y'))
        except ValueError:
            self.date_var.set(s.period_start)
        self._loading_metadata = False
        try:
            filename, page = s.source.rsplit('#page', 1)
            self.current_image = load_pages(filename)[int(page)-1]
        except Exception:
            self.current_image = None
            self.img_label.config(image='',text='Source photo could not be opened')
            self.row_preview.config(image='',text='No source row available')
            self.note_var.set('Original photo no longer found. Reimport the source before approving the timesheet.')
        self.refresh_days()
        self.update_preview()
        self.tree.selection_set('0')
        self.tree.focus('0')
        self.select_day()

    def refresh_days(self):
        self.tree.delete(*self.tree.get_children())
        if self.active_idx is None: return
        s = self.sheets[self.active_idx]
        for i, d in enumerate(s.days):
            hours, errors = calculate_day(d)
            unread = any(w.startswith(f'Week {i//7+1} {DISPLAY[i%7]},') for w in s.scan_warnings)
            flag = 'FIX' if errors else ('CHECK OCR' if unread else ('✓ Checked' if s.reviewed_days[i] else 'REVIEW'))
            tag = 'issue' if (errors or unread) else ('week' if i == 7 else 'odd' if i % 2 else '')
            vals = [f'W{i//7+1} {DISPLAY[i%7][:3]}', *(display_time(getattr(d,k)) for k in TIME_FIELDS),
                    f'{hours:.2f}' if hours is not None else '—', flag]
            self.tree.insert('', 'end', iid=str(i), values=vals, tags=(tag,))
        self._set_totals()
        self.refresh_list()

    def _set_totals(self):
        if self.active_idx is None: return
        s = summarize(self.sheets[self.active_idx])
        def fmt(v): return 'Check entries' if v is None else f'{v:.2f}'
        self.totals.set(f'Week 1: {fmt(s["week1"])} h     Week 2: {fmt(s["week2"])} h     Total: {fmt(s["total"])} h')

    def _punch_changed(self, *_args):
        if self._loading_punches or self._editing_day is None:
            return
        sheet_index, row_index = self._editing_day
        if sheet_index >= len(self.sheets):
            return
        sheet = self.sheets[sheet_index]
        day = sheet.days[row_index]
        values = [v.get().strip() for v in self.punch_vars]
        if values == [getattr(day, k) for k in TIME_FIELDS]:
            return
        for key, value in zip(TIME_FIELDS, values):
            if getattr(day,key) != value and key in day.blank_confirmed:
                day.blank_confirmed.remove(key)
                self.blank_vars[TIME_FIELDS.index(key)].set(False)
            setattr(day, key, value)
        sheet.reviewed_days[row_index] = False
        sheet.approved = False
        hours, errors = calculate_day(day)
        current = list(self.tree.item(str(row_index), 'values'))
        if current:
            current[1:5] = [display_time(value) for value in values]
            current[5:] = [f'{hours:.2f}' if hours is not None else '—', 'FIX' if errors else 'REVIEW']
            self.tree.item(str(row_index), values=current)
        self._set_totals()
        self.refresh_list()
        self._save()

    def select_day(self, _event=None):
        if self.active_idx is None: return
        sel = self.tree.selection()
        if not sel: return
        d = self.sheets[self.active_idx].days[int(sel[0])]
        self._loading_punches = True
        try:
            for v,k in zip(self.punch_vars,TIME_FIELDS):
                v.set(getattr(d,k))
            for v,k in zip(self.blank_vars,TIME_FIELDS):
                v.set(k in d.blank_confirmed)
        finally:
            self._loading_punches = False
        self._editing_day = (self.active_idx, int(sel[0]))
        h, errors = calculate_day(d)
        warnings = [w for w in self.sheets[self.active_idx].scan_warnings
                    if w.startswith(f'Week {int(sel[0])//7+1} {DISPLAY[int(sel[0])%7]},')]
        self.note_var.set(('⚠ ' + '; '.join(errors or warnings)) if (errors or warnings) else 'Read the handwritten row on the right. Correct any OCR mistakes, then click Checked: Save & Next. Blank days may remain blank.')
        self.update_preview()

    def _blank_changed(self):
        if self._editing_day is None:return
        si,row = self._editing_day
        sheet = self.sheets[si]
        sheet.days[row].blank_confirmed = [k for k,v in zip(TIME_FIELDS,self.blank_vars) if v.get()]
        sheet.reviewed_days[row] = False
        sheet.approved = False
        self._save()

    def save_day(self):
        if self.active_idx is None: return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Select a day','Select a row in the table first.')
            return
        s = self.sheets[self.active_idx]
        i = int(sel[0]); d = s.days[i]
        for v,k in zip(self.punch_vars,TIME_FIELDS):
            setattr(d,k,v.get().strip())
        # Saving an entire row marks its OCR warnings as manually reviewed.
        # This action does not approve the employee sheet or bypass validation.
        prefix = f'Week {i//7+1} {DISPLAY[i%7]},'
        try:
            mark_row_reviewed(s,i)
        except ValueError as exc:
            s.reviewed_days[i] = False
            self._save()
            messagebox.showwarning('Check this day',str(exc))
            return
        s.scan_warnings = [warning for warning in s.scan_warnings if not warning.startswith(prefix)]
        s.approved = False
        self.refresh_days(); self.tree.selection_set(str(i)); self.tree.focus(str(i))
        self._save()
        self.select_day()
        _, errs = calculate_day(d)
        if errs: messagebox.showwarning('Check this day','\n'.join(errs))
        else:
            next_i = (i+1) % 14
            self.tree.selection_set(str(next_i)); self.tree.focus(str(next_i)); self.tree.see(str(next_i)); self.select_day()
            self.punch_entries[0].focus_set()

    def update_preview(self):
        if self.current_image is None: return
        try:
            w = max(200, self.img_label.winfo_width()-8)
            h = max(250, self.img_label.winfo_height()-8)
            base = self.current_image.copy()
            chosen = self.tree.selection()
            if chosen:
                i = int(chosen[0])
                draw = ImageDraw.Draw(base)
                rect = self._row_box(base,i)
                draw.rectangle(rect, outline='#FF5533', width=max(3, int(base.width/250)))
            base.thumbnail((w,h), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(base)
            self.img_label.config(image=self.preview_photo, text='')
            if chosen:
                i=int(chosen[0])
                snippet = self.current_image.crop(self._row_box(self.current_image,i))
                snippet.thumbnail((w,105), Image.Resampling.LANCZOS)
                # Keep separate reference alive.
                self._row_image=ImageTk.PhotoImage(snippet)
                self.row_preview.config(image=self._row_image, text='')
        except (tk.TclError, ValueError, IndexError):
            pass

    def zoom_day(self):
        """Large readable handwriting popup for quick verification without another app."""
        selected = self.tree.selection()
        if self.current_image is None or not selected:
            messagebox.showinfo('Choose a row', 'Select a day after importing a timesheet.')
            return
        i = int(selected[0])
        box = self._row_box(self.current_image,i)
        strip = self.current_image.crop(box)
        strip = strip.resize((max(950,strip.width*2), max(90,strip.height*2)), Image.Resampling.LANCZOS)
        popup = tk.Toplevel(self)
        popup.title(f'Enlarged handwriting — Week {i//7+1}, {DISPLAY[i%7]}')
        popup.resizable(True, True)
        popup.geometry('1050x250')
        ttk.Label(popup, text=f'Week {i//7+1} — {DISPLAY[i%7]} | Compare the clock times with the source photo', padding=12).pack(anchor='w')
        photo = ImageTk.PhotoImage(strip)
        label = ttk.Label(popup, image=photo)
        label.image = photo
        label.pack(fill='both', expand=True, padx=12, pady=8)
        ttk.Button(popup, text='Close', command=popup.destroy).pack(pady=(0,8))

    def _row_box(self,image,row):
        sheet = self.sheets[self.active_idx] if self.active_idx is not None else None
        if sheet and len(sheet.review_boxes) == 14:
            return tuple(sheet.review_boxes[row])
        # An unregistered sheet has no defensible row highlight. Show the
        # complete source rather than an unrelated header or neighboring day.
        if sheet:
            return (0,0,image.width,image.height)
        top,bottom = ROW_Y[row]
        return (int(175*image.width/REF_W),int((top-6)*image.height/REF_H),
                int(758*image.width/REF_W),int((bottom+6)*image.height/REF_H))

    def approve(self):
        if self.active_idx is None:
            messagebox.showinfo('Nothing to approve','Add a timesheet first.')
            return
        self.capture_metadata()
        s = self.sheets[self.active_idx]
        errors = review_issues(s)
        if errors:
            messagebox.showwarning('Correct these entries first', '\n'.join(errors[:14]))
            return
        if self.current_image is None:
            messagebox.showwarning('Photo missing','The source photo is missing. Reimport the photo before approving.')
            return
        unread_count = max(0, len(s.scan_warnings)-1)
        detail = (f'\n\nWARNING: OCR could not read {unread_count} potentially written cells. Check those cells against the photo, including any blank rows.' if unread_count else '')
        if not messagebox.askyesno('Confirm reviewed', f'Have you checked every handwritten punch for {s.employee} against the original picture?{detail}\n\nThis approves the sheet for payroll export.'):
            return
        mark_sheet_approved(s)
        self._save(); self.refresh_list()
        self.status.set(f'Approved {s.employee}. Select the next timesheet or Export Excel.')

    def export(self):
        if self.recovery_issues:
            messagebox.showwarning('Resolve recovery problems before export','\n'.join(self.recovery_issues))
            return
        if self.busy:
            messagebox.showwarning('Timesheets are still importing','Wait for every selected file to finish importing before exporting payroll.')
            return
        self.capture_metadata()
        if not self.sheets:
            messagebox.showinfo('Nothing to export','Add timesheets first.')
            return
        issues=[]
        for s in self.sheets:
            if not s.approved: issues.append(f'{s.employee or Path(s.source).stem}: not approved')
            issues.extend(f'{s.employee}: {v}' for v in review_issues(s))
        if issues:
            messagebox.showwarning('Finish review before export', '\n'.join(issues[:22]))
            return
        path = filedialog.asksaveasfilename(title='Save payroll Excel file for Kansas City', defaultextension='.xlsx',
                initialfile=f'KC_Payroll_{self.sheets[0].period_start}.xlsx',
                filetypes=[('Excel Workbook','*.xlsx')])
        if not path:return
        try:
            export_excel(path, self.sheets)
        except Exception as e:
            messagebox.showerror('Could not export',str(e));return
        self.status.set(f'Exported Excel payroll: {path}')
        if messagebox.askyesno('Payroll exported',f'Payroll workbook created:\n\n{path}\n\nOpen it now?'):
            try: os.startfile(path)  # Windows
            except AttributeError:
                import subprocess
                subprocess.Popen(['xdg-open',path])

    def new_period(self):
        if self.busy:return
        if not messagebox.askyesno('Start new pay period', 'Clear the current working list?\n\nExport your current period first if needed. The original timesheet pictures will NOT be deleted.'):
            return
        self.capture_metadata()
        if self.sheets:
            history = app_dir()/'previous-payrolls'/f'payroll-{datetime.now():%Y%m%d-%H%M%S-%f}.json'
            try:save_session(str(history),self.sheets)
            except OSError as exc:
                messagebox.showerror('Could not preserve this payroll',str(exc));return
        self._editing_day = None
        self.recovery_issues=[]
        self.sheets = []; self.active_idx = None; self.current_image = None
        self.sheet_list.delete(0,'end'); self.tree.delete(*self.tree.get_children())
        self.name_var.set(''); self.date_var.set('')
        self.img_label.config(image='',text='Import a photo to see it here')
        self.row_preview.config(image='',text='Selected row will appear here')
        self.totals.set('Week 1: —    Week 2: —    Total: —')
        self._save(); self.status.set('New payroll started. Add photos to begin.')

    def close(self):
        if self.busy:
            if not messagebox.askyesno('Scan in progress','Close before scanning finishes?'):
                return
            self._cancel_import.set()
        self.capture_metadata()
        self._save();self.destroy()

    def destroy(self):
        if hasattr(self,'_session_lock'):
            self._session_lock.close()
        super().destroy()


def main():
    PayrollApp().mainloop()
