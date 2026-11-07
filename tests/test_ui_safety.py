"""Exercise real desktop widgets on Windows or a virtual display."""
import os
import pytest
from PIL import Image
from app.core import Sheet, ShiftDay, load_session
from tests.helpers import approve_sheet

pytestmark = pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='GUI display required')

@pytest.fixture
def ui(tmp_path, monkeypatch):
    import app.ui as module
    monkeypatch.setattr(module, 'app_dir', lambda: tmp_path)
    monkeypatch.setattr(module.messagebox, 'showwarning', lambda *a, **k: None)
    app = module.PayrollApp()
    photo = tmp_path/'photo.png'
    Image.new('RGB', (958,1350), 'white').save(photo)
    sheet = Sheet(str(photo)+'#page1', 'hash', 'Person', '2026-10-24',
                  approved=True, reviewed_days=[True]*14)
    sheet.days[0] = ShiftDay('8A','4P')
    approve_sheet(sheet,tmp_path)
    app.sheets = [sheet]
    app.refresh_list()
    app.show_sheet(0)
    app.update()
    yield app, sheet, tmp_path
    app.destroy()

def test_correction_survives_row_switch_and_revokes_approval(ui):
    app, sheet, folder = ui
    app.punch_vars[1].set('5P')
    assert sheet.days[0].out1 == '5P'
    assert not sheet.approved and not sheet.reviewed_days[0]
    app.tree.selection_set('1'); app.select_day()
    app.tree.selection_set('0'); app.select_day()
    assert app.punch_vars[1].get() == '5P'
    assert load_session(str(folder/'current_session.json'))[0].days[0].out1 == '5P'

def test_row_display_preserves_approval(ui):
    app, sheet, _ = ui
    app.tree.selection_set('1'); app.select_day()
    assert sheet.approved and all(sheet.reviewed_days)

def test_duplicates_in_one_import_are_skipped(ui):
    app, sheet, _ = ui
    app._complete_import([Sheet(sheet.source, 'new', 'Second', '2026-10-24'),
                          Sheet(sheet.source, 'new', 'Second', '2026-10-24')], [])
    assert len(app.sheets) == 2


def test_recovery_deduplicates_pending_import_with_same_archive_bytes(ui):
    from app.storage import journal_import

    app, sheet, folder = ui
    assert app._save()
    duplicate = Sheet.from_dict(sheet.to_dict())
    duplicate.source_hash = 'different-encoding'
    journal = journal_import(duplicate, folder / 'pending-imports')
    app.sheets = []
    app.active_idx = None
    app._restore_session()
    assert len(app.sheets) == 1
    assert app.sheets[0].approved
    assert not journal.exists()


def test_partial_pay_period_date_is_not_copied_to_other_employees(ui):
    app,sheet,_=ui
    second=Sheet(sheet.source,'second','Second')
    app.sheets.append(second)
    app.date_var.set('1')
    assert second.period_start == ''
    app.date_var.set('11/07/2026')
    assert second.period_start == '2026-11-07'
    assert not sheet.approved


def test_unreadable_writing_needs_an_explicit_blank_confirmation(ui):
    app,sheet,_=ui
    day=sheet.days[1]
    day.observations['in1']={'status':'unreadable-or-invalid','raw':''}
    sheet.reviewed_days[1]=False
    app.tree.selection_set('1');app.select_day();app.save_day()
    assert not sheet.reviewed_days[1]
    app.blank_vars[0].set(True);app._blank_changed();app.save_day()
    assert sheet.reviewed_days[1]


def test_new_import_does_not_interrupt_the_row_being_reviewed(ui):
    app,sheet,_=ui
    app.tree.selection_set('4');app.select_day()
    app._complete_import([Sheet(sheet.source,'different','Second')],[])
    assert app.active_idx == 0
    assert app.tree.selection()==('4',)


def test_installed_workflow_uses_actual_import_review_approval_export_and_restart():
    from app.smoke import run_workflow_smoke
    assert run_workflow_smoke() == 0


def test_export_is_blocked_while_selected_forms_are_still_importing(ui,monkeypatch):
    app,sheet,_=ui
    app.busy=True
    import app.ui as module
    monkeypatch.setattr(module.filedialog,'asksaveasfilename',lambda **k:pytest.fail('Export dialog opened during import'))
    app.export()


def test_time_entry_and_check_button_remain_visible_on_a_small_laptop(ui):
    app,sheet,_=ui
    app.minsize(900,600);app.geometry('1060x680');app.update()
    bottom=app.winfo_rooty()+app.winfo_height()
    for widget in (app.punch_entries[0],app.punch_entries[1],app.btn_save_day):
        assert widget.winfo_viewable()
        assert widget.winfo_rooty()+widget.winfo_height() <= bottom


def test_single_pair_form_shows_only_its_two_clock_fields(ui):
    app,sheet,_=ui
    sheet.form_type='comfort_suites_single_pair';app.show_sheet(0);app.update()
    assert not app.punch_entries[2].winfo_viewable()
    assert app.tree['displaycolumns']==('day','in1','out1','hours','review')
