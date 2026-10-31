"""Download only pinned public model weights during installation/build setup."""
from pathlib import Path
import hashlib
import sys
import tempfile
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.model_assets import LINE_MODEL, LINE_MODEL_SHA256, LINE_MODEL_URL


def fetch_model(destination=LINE_MODEL):
    destination = Path(destination)
    if destination.is_file():
        with destination.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() == LINE_MODEL_SHA256:
                print('Verified handwriting model', flush=True)
                return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.part', delete=False) as output:
            temporary = Path(output.name)
            digest = hashlib.sha256()
            request = Request(LINE_MODEL_URL, headers={'User-Agent': 'HotelPayrollAssistant-build'})
            with urlopen(request, timeout=120) as response:
                while chunk := response.read(1024*1024):
                    output.write(chunk)
                    digest.update(chunk)
            if digest.hexdigest() != LINE_MODEL_SHA256:
                raise RuntimeError('Downloaded handwriting model failed SHA-256 verification')
        temporary.replace(destination)
        print('Downloaded and verified handwriting model', flush=True)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    fetch_model()
