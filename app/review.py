"""Safety checks independent of desktop UI; payroll requires visual review."""
from pathlib import Path
import os
import tempfile
from PIL import Image, ImageOps
from .core import (Sheet, TIME_FIELDS, validate_sheet, fully_reviewed, calculate_day,
                   digest_bytes, row_fingerprint, sheet_fingerprint)


def archive_page(sheet: Sheet, image: Image.Image, directory: Path) -> Sheet:
    """Persist a private copy; changes to the phone's photo folder cannot remove evidence."""
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / (digest_bytes(sheet.source_hash.encode()) + '.png')
    handle = tempfile.NamedTemporaryFile(dir=directory,suffix='.tmp.png',delete=False)
    tmp = Path(handle.name)
    handle.close()
    archival = ImageOps.exif_transpose(image).convert('RGB')
    rotation = sheet.archive_rotation or (180 if sheet.rotate_180_for_archive else 0)
    if rotation:
        archival = archival.rotate(rotation, expand=True)
    try:
        archival.save(tmp, 'PNG', optimize=True)
        with tmp.open('r+b') as stream:
            os.fsync(stream.fileno())
        expected = digest_bytes(tmp.read_bytes())
        if destination.exists() and digest_bytes(destination.read_bytes()) != expected:
            # Reimporting the actual source repairs a changed archive, but
            # preserves the previous bytes and invalidates stale approvals.
            previous = destination.with_name(destination.stem+'.preserved-'+digest_bytes(destination.read_bytes())+'.png')
            if not previous.exists():
                from .core import _atomic_write
                _atomic_write(previous,destination.read_bytes())
        if not destination.exists() or digest_bytes(destination.read_bytes()) != expected:
            tmp.replace(destination)
    finally:
        tmp.unlink(missing_ok=True)
    sheet.source = str(destination) + '#page1'
    actual = digest_bytes(destination.read_bytes())
    if sheet.archived_hash and sheet.archived_hash != actual:
        raise ValueError('Archived timesheet image changed; reimport and review it')
    sheet.archived_hash = actual
    return sheet


def scan_available(sheet: Sheet) -> bool:
    return Path(sheet.source.split('#page')[0]).is_file()


def review_issues(sheet: Sheet) -> list[str]:
    issues = validate_sheet(sheet)
    if not scan_available(sheet):
        issues.append('The original timesheet image is missing')
    elif sheet.archived_hash and digest_bytes(Path(sheet.source.split('#page')[0]).read_bytes()) != sheet.archived_hash:
        issues.append('The original timesheet image changed; reimport and review it')
    if not fully_reviewed(sheet.reviewed_days):
        count = sum(v is True for v in sheet.reviewed_days) if isinstance(sheet.reviewed_days, list) else 0
        issues.append(f'Only {count} of 14 day rows confirmed against the photo')
    if (len(sheet.row_fingerprints) != 14 or len(sheet.days) != 14 or
            any(sheet.row_fingerprints[i] != row_fingerprint(sheet,i) for i in range(min(14,len(sheet.days),len(sheet.row_fingerprints))))):
        issues.append('Day rows changed or have no recorded visual review')
    for i,day in enumerate(sheet.days):
        for key in unresolved_empty_fields(day):
            issues.append(f'Row {i+1}: {key} has unresolved writing; enter its time or explicitly confirm it is blank/crossed out')
    return issues


def unresolved_empty_fields(day) -> list[str]:
    return [key for key in TIME_FIELDS if not getattr(day,key).strip()
            and key not in day.blank_confirmed
            and (day.observations.get(key,{}).get('status','blank') != 'blank'
                 or bool(day.recognized.get(key,'')))]


def mark_row_reviewed(sheet: Sheet, row: int) -> None:
    errors = calculate_day(sheet.days[row])[1]
    if errors:
        raise ValueError('; '.join(errors))
    unresolved = unresolved_empty_fields(sheet.days[row])
    if unresolved:
        raise ValueError('Writing needs a time or explicit blank/crossed-out confirmation: '+', '.join(unresolved))
    sheet.reviewed_days[row] = True
    sheet.row_fingerprints[row] = row_fingerprint(sheet,row)
    sheet.approved = False
    sheet.approval_fingerprint = ''


def mark_sheet_approved(sheet: Sheet) -> None:
    issues = review_issues(sheet)
    if issues:
        raise ValueError('\n'.join(issues))
    if not sheet.archived_hash:
        sheet.archived_hash = digest_bytes(Path(sheet.source.split('#page')[0]).read_bytes())
    sheet.approved = True
    sheet.approval_fingerprint = sheet_fingerprint(sheet)


def approval_current(sheet: Sheet) -> bool:
    return (sheet.approved is True and bool(sheet.approval_fingerprint)
            and sheet.approval_fingerprint == sheet_fingerprint(sheet))
