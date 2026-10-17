"""The text turn client, without calling Gemini."""

import json
import os
import unittest
from unittest.mock import patch

from try_turn import TurnError, ask, strip_nulls


class Reply:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def gemini_body(turn):
    return {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps({"turn": turn})}]}}
        ]
    }


class TurnClientTest(unittest.TestCase):
    def test_nulls_drop_out(self):
        self.assertEqual(strip_nulls({"op": "say", "say": "Hi", "app": None}), {"op": "say", "say": "Hi"})

    def test_missing_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            with patch("try_turn.load_env"):
                with self.assertRaises(TurnError):
                    ask("hello", [])

    def test_inner_turn(self):
        turn = {"op": "say", "say": "Hi", "app": None}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("try_turn.load_env"):
                with patch("try_turn.urllib.request.urlopen", return_value=Reply(gemini_body(turn))):
                    parsed = ask("hello", [])
        self.assertEqual(parsed, {"op": "say", "say": "Hi"})

    def test_wav_is_attached_to_the_request(self):
        captured = {}

        def opener(request, timeout=0):
            captured["body"] = json.loads(request.data.decode())
            return Reply(gemini_body({"op": "say", "say": "Heard"}))

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("try_turn.load_env"):
                with patch("try_turn.urllib.request.urlopen", opener):
                    ask("", [], wav_base64="abc")
        parts = captured["body"]["contents"][0]["parts"]
        self.assertEqual(parts[0]["inlineData"]["data"], "abc")
        self.assertEqual(parts[0]["inlineData"]["mimeType"], "audio/wav")


if __name__ == "__main__":
    unittest.main()
