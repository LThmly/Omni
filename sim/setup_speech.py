#!/usr/bin/env python3
"""Download an official English Vosk model for offline recognition."""
import argparse
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

MODEL = 'vosk-model-small-en-us-0.15'
MODEL_CHOICES = {'small': (MODEL, 40),
                 'accurate': ('vosk-model-en-us-0.22-lgraph', 128)}
MODELS = Path(__file__).resolve().parent / 'models'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=MODEL_CHOICES, default='small',
                        help='small: Pi-friendly default; accurate: larger streaming model, benchmark before using on a Pi 3')
    args = parser.parse_args()
    model_name, size = MODEL_CHOICES[args.model]
    destination = MODELS / model_name
    if (destination / 'am' / 'final.mdl').exists():
        print(f'Model ready: {destination}')
        return
    MODELS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='download-', dir=MODELS) as temporary:
        temporary = Path(temporary)
        archive = temporary / 'model.zip'
        print(f'Downloading {model_name} (about {size} MB)…', flush=True)
        urllib.request.urlretrieve(f'https://alphacephei.com/vosk/models/{model_name}.zip', archive)
        with zipfile.ZipFile(archive) as source:
            for item in source.infolist():
                resolved = (temporary / item.filename).resolve()
                if not resolved.is_relative_to(temporary.resolve()):
                    raise RuntimeError('Invalid model archive path')
            source.extractall(temporary)
        model = temporary / model_name
        if not (model / 'am' / 'final.mdl').is_file():
            raise RuntimeError('Incomplete Vosk model')
        if destination.exists():
            raise RuntimeError(f'Incomplete directory already exists: {destination}; choose another model directory')
        shutil.move(str(model), destination)
    print(f'Model ready: {destination}')


if __name__ == '__main__':
    main()
