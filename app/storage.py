"""Recover durable imports and prevent two windows overwriting one payroll."""
from pathlib import Path
from .core import Sheet, save_session, load_session, digest_bytes


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
