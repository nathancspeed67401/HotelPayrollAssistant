"""Launch the desktop application, or exercise packaged dependencies without a GUI."""
from __future__ import annotations
import sys


def self_test() -> int:
    import tempfile
    from pathlib import Path
    from PIL import Image, ImageDraw
    import pytesseract
    from app.ocr import configure_tesseract
    from app.core import Sheet, ShiftDay, summarize
    from app.report import export_excel

    configure_tesseract()
    # Verify that the bundled optional handwriting recognizer and model load.
    from app.handwriting import _model, recognize_time
    assert len(_model().classes_) >= 12
    assert recognize_time(Image.new('RGB',(100,30),'white'))[0] == ''
    with tempfile.TemporaryDirectory(prefix='hotel-payroll-test-') as location:
        dest = Path(location)
        img = Image.new('RGB', (380, 95), 'white')
        ImageDraw.Draw(img).text((18, 15), '12:30 PM', fill='black')
        # Confirms both a real Tesseract executable and traineddata are reachable.
        pytesseract.image_to_string(img, config='--psm 7')
        sheet = Sheet(str(dest/'sample.png')+'#page1', 'sample', 'Installation Test',
                      '2026-10-24', approved=True, reviewed_days=[True]*14)
        sheet.days[0] = ShiftDay('11P', '7A')
        sheet.days[7] = ShiftDay('12A', '8A')
        img.save(dest / 'sample.png')
        assert summarize(sheet)['total'] == 16.0
        output = dest / 'payroll.xlsx'
        export_excel(str(output), [sheet])
        assert output.is_file() and output.stat().st_size > 1000
    return 0


if __name__ == '__main__':
    if '--gui-self-test' in sys.argv:
        from app.ui import PayrollApp
        app = PayrollApp()
        app.update()
        app.destroy()
        sys.exit(0)
    if '--self-test' in sys.argv:
        try:
            sys.exit(self_test())
        except Exception:
            import traceback
            from pathlib import Path
            import os
            dest = Path(os.getenv('TEMP') or '.') / 'HotelPayrollAssistant_self_test_error.txt'
            dest.write_text(traceback.format_exc(), encoding='utf-8')
            sys.exit(1)
    from app.ui import main
    main()
