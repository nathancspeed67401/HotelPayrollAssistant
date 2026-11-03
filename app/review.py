"""Safety checks independent of desktop UI; payroll requires visual review."""
from pathlib import Path
from PIL import Image, ImageOps
from .core import Sheet, validate_sheet, fully_reviewed


def archive_page(sheet: Sheet, image: Image.Image, directory: Path) -> Sheet:
    """Persist a private copy; changes to the phone's photo folder cannot remove evidence."""
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / (sheet.source_hash + '.png')
    if not destination.exists():
        tmp = destination.with_suffix('.tmp.png')
        archival = ImageOps.exif_transpose(image).convert('RGB')
        if sheet.rotate_180_for_archive:
            archival = archival.rotate(180, expand=True)
        archival.save(tmp, 'PNG', optimize=True)
        tmp.replace(destination)
    sheet.source = str(destination) + '#page1'
    return sheet


def scan_available(sheet: Sheet) -> bool:
    return Path(sheet.source.split('#page')[0]).is_file()


def review_issues(sheet: Sheet) -> list[str]:
    issues = validate_sheet(sheet)
    if not scan_available(sheet):
        issues.append('The original timesheet image is missing')
    if not fully_reviewed(sheet.reviewed_days):
        count = sum(v is True for v in sheet.reviewed_days) if isinstance(sheet.reviewed_days, list) else 0
        issues.append(f'Only {count} of 14 day rows confirmed against the photo')
    return issues
