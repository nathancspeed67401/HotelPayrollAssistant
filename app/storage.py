"""Recover durable imports and prevent two windows overwriting one payroll."""
from pathlib import Path
from .core import Sheet, save_session, load_session, digest_bytes, valid_period
from .review import source_issue


def journal_import(sheet: Sheet, directory: Path) -> Path:
    directory.mkdir(parents=True,exist_ok=True)
    path = directory/(digest_bytes(sheet.source_hash.encode())+'.json')
    save_session(str(path),[sheet])
    return path


def recover_imports(directory: Path, errors=None) -> list[tuple[Path,Sheet]]:
    recovered=[]
    for path in sorted(directory.glob('*.json')):
        try:
            recovered.extend((path,sheet) for sheet in load_session(str(path)))
        except (OSError,ValueError,TypeError,KeyError) as exc:
            if errors is None:raise
            errors.append(f'Interrupted import could not be recovered: {path.name} ({type(exc).__name__})')
    return recovered


def merge_imports(sheets: list[Sheet], incoming: list[Sheet]) -> tuple[int, int]:
    """Add unique pages and repair a missing source only with identical bytes."""
    originals = {sheet.source_hash: sheet for sheet in sheets}
    images = {sheet.archived_hash: sheet for sheet in sheets if sheet.archived_hash}
    period = next((sheet.period_start for sheet in sheets if valid_period(sheet.period_start)), '')
    added = repaired = 0
    for page in incoming:
        duplicate = originals.get(page.source_hash) or images.get(page.archived_hash)
        if duplicate is not None:
            if (page.archived_hash and page.archived_hash == duplicate.archived_hash
                    and page.source != duplicate.source and source_issue(duplicate) and not source_issue(page)):
                duplicate.source = page.source
                duplicate.approved = False
                duplicate.approval_fingerprint = ''
                repaired += 1
            continue
        page.period_start = page.period_start or period
        sheets.append(page)
        originals[page.source_hash] = page
        if page.archived_hash:
            images[page.archived_hash] = page
        added += 1
    return added, repaired


class SessionLock:
    def __init__(self, directory: Path):
        import os
        directory.mkdir(parents=True,exist_ok=True)
        self.stream = (directory/'session.lock').open('a+b')
        try:
            self.stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                if not self.stream.read(1):
                    self.stream.write(b'0');self.stream.flush()
                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            raise RuntimeError('Hotel Payroll Assistant is already open. Use the existing window.') from None

    def close(self):
        if not self.stream.closed:
            self.stream.close()
