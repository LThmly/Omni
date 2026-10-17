#!/usr/bin/env python3
"""Download the official small English Vosk model for offline recognition."""
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

MODEL = 'vosk-model-small-en-us-0.15'
MODELS = Path(__file__).resolve().parent / 'models'
URL = f'https://alphacephei.com/vosk/models/{MODEL}.zip'


def main():
    destination = MODELS / MODEL
    if (destination / 'am' / 'final.mdl').exists():
        print(f'Model ready: {destination}')
        return
    MODELS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='download-', dir=MODELS) as temporary:
        temporary = Path(temporary)
        archive = temporary / 'model.zip'
        print(f'Downloading {MODEL} (about 40 MB)…', flush=True)
        urllib.request.urlretrieve(URL, archive)
        with zipfile.ZipFile(archive) as source:
            for item in source.infolist():
                resolved = (temporary / item.filename).resolve()
                if not resolved.is_relative_to(temporary.resolve()):
                    raise RuntimeError('Invalid model archive path')
            source.extractall(temporary)
        model = temporary / MODEL
        if not (model / 'am' / 'final.mdl').is_file():
            raise RuntimeError('Incomplete Vosk model')
        if destination.exists():
            raise RuntimeError(f'Incomplete directory already exists: {destination}; choose another model directory')
        shutil.move(str(model), destination)
    print(f'Model ready: {destination}')


if __name__ == '__main__':
    main()
