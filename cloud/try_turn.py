#!/usr/bin/env python3
"""Send one utterance to Gemini and print a contract turn.

The model is constrained to contract/turn.strict.json. The schema root is
{"turn": {...}} and this script prints the inner object, which is what the
device stores.

  echo 'GEMINI_API_KEY=...' > .env
  python3 cloud/try_turn.py "Add milk to my shopping list."
  python3 cloud/try_turn.py "Add coffee" --registry contract/fixtures/registry.json
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contract" / "turn.strict.json").read_text())


class TurnError(Exception):
    """The model call did not return a usable turn."""

SYSTEM = """You fill one Omni turn for a portrait phone.

Modules already on the device are listed in registry. Each has an id.
checklist: items with label and checked. scoreboard: two sides with name and score.
progress: label, unit, value, goal, step. key_value: rows of label and value.

propose when no registry app covers the request. confirm is true. say is a short question. Invent a short id.
mutate when a registry app covers it. Use that app's id. append sets args.label. add sets args.amount. Other actions leave both args null.
say when the request is not one of these apps.

cursor starts at 0. Scores start at 0."""


def load_env():
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def strip_nulls(value):
    if isinstance(value, dict):
        return {key: strip_nulls(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [strip_nulls(item) for item in value]
    return value


def candidate_text(body):
    if body.get("error"):
        message = (body["error"].get("message") or "request failed").strip()
        raise TurnError(message)
    candidates = body.get("candidates") or []
    if not candidates:
        raise TurnError("Gemini returned no candidates.")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    texts = [part["text"] for part in parts if part.get("text") and not part.get("thought")]
    if not texts:
        raise TurnError("Gemini returned no JSON text.")
    return texts[-1]


def ask(text, registry, wav_base64=None):
    """Send text, or a recorded wav, plus the apps already on the device."""
    load_env()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    if not key:
        raise TurnError("Set GEMINI_API_KEY in .env at the repo root.")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    parts = []
    if wav_base64:
        parts.append({
            "inlineData": {
                "mimeType": "audio/wav",
                "data": wav_base64,
            }
        })
    user_payload = {"text": text or "User spoke. Listen to the audio and generate the turn JSON.", "registry": registry}
    parts.append({"text": json.dumps(user_payload)})
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": SCHEMA,
        },
    }
    # This key is bound to the Vertex express service account and restricted to
    # Agent Platform. It cannot call generativelanguage.googleapis.com.
    req = urllib.request.Request(
        "https://aiplatform.googleapis.com/v1/publishers/google/models/%s:generateContent" % model,
        data=json.dumps(payload).encode(),
        headers={
            "x-goog-api-key": key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            body = json.loads(res.read().decode())
    except urllib.error.HTTPError as err:
        detail = err.read().decode()[:800]
        print("Gemini %s: %s" % (err.code, detail), file=sys.stderr)
        raise TurnError("Gemini returned HTTP %s." % err.code) from err
    except urllib.error.URLError as err:
        raise TurnError("Could not reach Gemini.") from err
    try:
        wrapped = json.loads(candidate_text(body))
    except json.JSONDecodeError as err:
        raise TurnError("Gemini reply was not JSON.") from err
    turn = wrapped.get("turn", wrapped) if isinstance(wrapped, dict) else None
    turn = strip_nulls(turn)
    if not isinstance(turn, dict) or turn.get("op") not in ("propose", "mutate", "say"):
        raise TurnError("Gemini returned an unexpected turn.")
    return turn


def main():
    parser = argparse.ArgumentParser(description="One structured Omni turn.")
    parser.add_argument("text", help="What the user said.")
    parser.add_argument("--registry", type=Path, help="JSON file of apps already on the device.")
    args = parser.parse_args()
    registry = []
    if args.registry:
        registry = json.loads(args.registry.read_text())
    try:
        turn = ask(args.text, registry)
    except TurnError as exc:
        raise SystemExit(str(exc))
    json.dump(turn, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
