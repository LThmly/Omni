#!/usr/bin/env python3
"""Keyword /v1/turn for firmware and the simulator. Not the demo model."""

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "contract" / "fixtures"


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


def respond(body):
    from contract.runtime import message,validate_turn,preview_navigation
    text=(body.get('text') or '').strip()
    registry=body.get('registry') or []
    if try_turn is not None:
        try_turn.load_env()
        if os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY'):
            # A failed Gemini call is an error, never a fabricated preview app.
            return try_turn.ask(text,registry,wav_base64=body.get('wav_base64'))
    navigate=preview_navigation(text,registry)
    if navigate:return validate_turn(navigate,registry)
    words=tokens(text)
    fixtures=ROOT/'v2'
    def example(name):return json.loads((fixtures/name).read_text())['turn']
    if has(words,'what','why','how','hello','hi'):
        return message('This is the offline preview. Enable Gemini for answers.')
    if has(words,'add','append') and has(words,'coffee','bread','eggs','milk'):
        target=next((app for app in registry if app.get('module')=='composed' and
                     any(field.get('id')=='items' for field in app['state']['fields']) and
                     any(field.get('id')=='entry' for field in app['state']['fields'])),None)
        if target:
            turn=example('update-shopping.json');turn['app_id']=target['id']
            turn['actions'][0]['value']=next(label for label in ('Coffee','Bread','Eggs','Milk') if has(words,label.lower()))
            turn['say']='Added '+turn['actions'][0]['value'].lower()+'.'
            return validate_turn(turn,registry)
    name='create-scoreboard.json' if has(words,'score','ping','pong') else 'create-hydration.json' if has(words,'water','ounce','hydrat') else 'create-shopping.json' if has(words,'milk','shopping','list') else None
    if not name:return message('This is the offline preview. Ask for a shopping list, scoreboard, or progress tracker.')
    turn=example(name);base=turn['app']['id'];suffix=2
    while any(app.get('id')==turn['app']['id'] for app in registry):
        turn['app']['id']=base+'_'+str(suffix);suffix+=1
    return validate_turn(turn,registry)


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
        try:result=respond(body)
        except (ValueError,TypeError,AttributeError):
            self.send_error(400,'Invalid turn request');return
        except try_turn.TurnError:
            payload=json.dumps({'error':'Gemini could not return a valid response.'}).encode()
            self.send_response(502);self._cors();self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
        payload = json.dumps(result).encode()
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
