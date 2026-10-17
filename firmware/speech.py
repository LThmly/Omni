"""Offline push-to-talk recognition. Audio/decoding stay off the pygame thread."""
from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

DEFAULT_MODEL = Path(__file__).resolve().parents[1] / 'sim' / 'models' / 'vosk-model-small-en-us-0.15'


class VoskSpeech:
    def __init__(self, model_path=DEFAULT_MODEL, device=None, *, model=None, audio=None, recognizer_factory=None):
        # Optional adapters let tests exercise capture/flush without a microphone.
        if audio is None:
            import sounddevice as audio
        if recognizer_factory is None or model is None:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)
            recognizer_factory = recognizer_factory or KaldiRecognizer
            if model is None:
                model_path = Path(model_path)
                if not (model_path / 'am' / 'final.mdl').exists():
                    raise RuntimeError('Vosk model missing. Run .venv/bin/python sim/setup_speech.py')
                print(f'Loading offline speech model: {model_path}', flush=True)
                model = Model(str(model_path))
        self.audio, self.model, self.recognizer_factory = audio, model, recognizer_factory
        self.device = device
        self.results = queue.Queue()
        self.number = 0
        self.session = None

    def start(self):
        if self.session and self.session['thread'].is_alive():
            raise RuntimeError('Microphone is still closing. Try again.')
        self.number += 1
        session = dict(id=self.number, stop=threading.Event(), cancel=threading.Event())
        worker = threading.Thread(target=self._capture, args=(session,), daemon=True, name='omni-vosk')
        session['thread'] = worker
        self.session = session
        worker.start()
        return session['id']

    def finish(self, number):
        if self.session and self.session['id'] == number:
            self.session['stop'].set()

    def cancel(self, number=None):
        if self.session and (number is None or self.session['id'] == number):
            self.session['cancel'].set()
            self.session['stop'].set()

    def poll(self):
        events = []
        while True:
            try: events.append(self.results.get_nowait())
            except queue.Empty: return events

    def close(self):
        self.cancel()
        if self.session:
            self.session['thread'].join(timeout=2)

    def _capture(self, session):
        samples = queue.Queue(maxsize=100)  # 10 seconds of 100 ms blocks.
        overflow = threading.Event()
        warned = threading.Event()
        number = session['id']
        segments = []
        previous = None

        def emit(kind, payload):
            if not session['cancel'].is_set(): self.results.put((number, kind, payload))

        def callback(data, frames, timing, status):
            if session['stop'].is_set(): return
            # PortAudio can report a transient overrun when a Pi is busy.
            # The current block is still usable; keep it and let ASR recover.
            if status and not warned.is_set():
                warned.set()
                emit('warning', str(status))
            try: samples.put_nowait(bytes(data))
            except queue.Full: overflow.set()

        try:
            info = self.audio.query_devices(self.device, 'input')
            rate = int(info['default_samplerate'])
            recognizer = self.recognizer_factory(self.model, rate)

            def consume(data):
                nonlocal previous
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get('text', '').strip()
                    if text: segments.append(text)
                    emit('segment', result)
                    previous = None
                else:
                    result = json.loads(recognizer.PartialResult())
                    partial = result.get('partial', '')
                    if partial != previous:
                        emit('partial', result)
                        previous = partial

            # Match the hardware's sample rate; Vosk resamples internally.
            with self.audio.RawInputStream(samplerate=rate, blocksize=max(1, rate//10),
                    device=self.device, dtype='int16', channels=1, latency=.2, callback=callback) as stream:
                emit('ready', {'device': info['name'], 'samplerate': rate})
                while not session['stop'].is_set():
                    if overflow.is_set(): raise RuntimeError('Microphone audio overflow. Try again.')
                    try: data = samples.get(timeout=.05)
                    except queue.Empty: continue
                    consume(data)
                stream.stop()
            if session['cancel'].is_set(): return
            # Decode every block captured before release, then flush Vosk.
            while not samples.empty(): consume(samples.get_nowait())
            if overflow.is_set(): raise RuntimeError('Microphone audio overflow. Try again.')
            final = json.loads(recognizer.FinalResult())
            text = final.get('text', '').strip()
            if text: segments.append(text)
            emit('final', {'text': ' '.join(segments)})
        except Exception as error:
            emit('error', str(error))
