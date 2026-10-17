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

SYSTEM = """You fill one Omni turn for a pocket e-ink device.

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
        message = body["error"].get("message") or json.dumps(body["error"])
        raise SystemExit("Gemini: " + message)
    candidates = body.get("candidates") or []
    if not candidates:
        raise SystemExit("Gemini returned no candidates: " + json.dumps(body)[:800])
    parts = (candidates[0].get("content") or {}).get("parts") or []
    texts = [part["text"] for part in parts if part.get("text") and not part.get("thought")]
    if not texts:
        raise SystemExit("Gemini returned no JSON text: " + json.dumps(body)[:800])
    return texts[-1]


def ask(text, registry):
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    if not key:
        raise SystemExit("Set GEMINI_API_KEY in .env at the repo root. That file stays untracked.")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [
            {
                "role": "user",
                "parts": [{"text": json.dumps({"text": text, "registry": registry})}],
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
        raise SystemExit("Gemini %s: %s" % (err.code, err.read().decode()[:800]))
    wrapped = json.loads(candidate_text(body))
    turn = wrapped.get("turn", wrapped)
    return strip_nulls(turn)


def main():
    parser = argparse.ArgumentParser(description="One structured Omni turn.")
    parser.add_argument("text", help="What the user said.")
    parser.add_argument("--registry", type=Path, help="JSON file of apps already on the device.")
    args = parser.parse_args()
    load_env()
    registry = []
    if args.registry:
        registry = json.loads(args.registry.read_text())
    json.dump(ask(args.text, registry), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
