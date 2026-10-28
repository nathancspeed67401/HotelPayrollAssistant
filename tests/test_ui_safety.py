"""Exercise real desktop widgets on Windows or a virtual display."""
import os
import pytest
from PIL import Image
from app.core import Sheet, ShiftDay, load_session

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
