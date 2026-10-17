#!/usr/bin/env python3
"""Keyword /v1/turn for firmware and the simulator. Not the demo model."""

import base64
import io
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "contract" / "fixtures"
TURNS = ROOT / "turns"


def load(name):
    return json.loads((TURNS / name).read_text())


def tokens(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def has(words, *needles):
    return any(word == needle or word.startswith(needle) for word in words for needle in needles)


# Allow importing try_turn
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import try_turn
except ImportError:
    try_turn = None


def transcribe_audio(wav_b64):
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        data = base64.b64decode(wav_b64)
        with io.BytesIO(data) as in_f, sr.AudioFile(in_f) as source:
            audio = r.record(source)
            return r.recognize_google(audio)
    except Exception:
        return ""


def respond(body):
    text = (body.get("text") or "").strip()
    wav_b64 = body.get("wav_base64")
    registry = body.get("registry") or []

    # 1. If Gemini API key is configured, query the real AI model
    if try_turn is not None and (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        try:
            return try_turn.ask(text, registry, wav_base64=wav_b64)
        except Exception as exc:
            print("Gemini call failed, falling back to stub:", exc)

    # 2. If audio was sent without text, try speech-to-text
    if wav_b64 and not text:
        text = transcribe_audio(wav_b64)

    words = tokens(text)
    has_list = any(app.get("module") == "checklist" for app in registry)

    if has(words, "score", "ping", "pong"):
        return load("propose-scoreboard.json")
    if has(words, "water", "ounce", "hydrat"):
        return load("propose-hydration.json")
    if has_list and has(words, "coffee", "bread", "eggs", "add"):
        return load("mutate-shopping.json")
    if has(words, "milk", "shopping", "list") and not has_list:
        return load("propose-shopping.json")

    # If spoken audio was provided in offline stub mode
    if wav_b64 and not words:
        if not has_list:
            return load("propose-shopping.json")
        else:
            return load("mutate-shopping.json")

    return load("say.json")


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/v1/turn":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            self.send_error(400)
            return
        payload = json.dumps(respond(body)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    print("omni stub on http://0.0.0.0:8787/v1/turn")
    ThreadingHTTPServer(("0.0.0.0", 8787), Handler).serve_forever()
