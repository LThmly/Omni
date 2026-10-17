"""The text turn client, without calling Gemini."""

import json
import os
import unittest
from unittest.mock import patch

from try_turn import TurnError, ask, strip_nulls, candidate_text, SYSTEM
from contract.runtime import message


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
            {"finishReason":"STOP","content": {"parts": [{"text": json.dumps({"turn": turn})}]}}
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
        turn = message("Hi")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("try_turn.load_env"):
                with patch("try_turn.urllib.request.urlopen", return_value=Reply(gemini_body(turn))):
                    parsed = ask("hello", [])
        self.assertEqual(parsed, message("Hi"))

    def test_wav_is_attached_to_the_request(self):
        captured = {}

        def opener(request, timeout=0):
            captured["body"] = json.loads(request.data.decode())
            return Reply(gemini_body(message("Heard")))

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("try_turn.load_env"):
                with patch("try_turn.urllib.request.urlopen", opener):
                    ask("", [], wav_base64="abc")
        parts = captured["body"]["contents"][0]["parts"]
        self.assertEqual(parts[0]["inlineData"]["data"], "abc")
        self.assertEqual(parts[0]["inlineData"]["mimeType"], "audio/wav")

    def test_rejects_truncation_prose_extras_and_wrong_intent_without_fallback(self):
        for turn in ({'op':'say','say':'Hi'}, {**message('Hi'),'app':None},
                     {**message('Hi'),'intent':'create_app','op':'propose'}):
            with patch.dict(os.environ,{'GEMINI_API_KEY':'test-key'}),patch('try_turn.load_env'),patch('try_turn.urllib.request.urlopen',return_value=Reply(gemini_body(turn))):
                with self.assertRaises(TurnError):ask('hello',[])
        body=gemini_body(message('Hi'));body['candidates'][0]['finishReason']='MAX_TOKENS'
        with self.assertRaises(TurnError):candidate_text(body)
        body['candidates'][0]['finishReason']='STOP'
        body['candidates'][0]['content']['parts']=[{'text':'hidden reasoning','thought':True},{'text':'{"turn":'},{'text':'{}}'}]
        self.assertEqual(candidate_text(body),'{'+'"turn":{}}')

    def test_navigation_classification_and_schema_are_sent_to_gemini(self):
        from contract.runtime import navigation
        turn=navigation('settings');captured={}
        def opener(request,timeout):
            captured.update(json.loads(request.data));return Reply(gemini_body(turn))
        with patch.dict(os.environ,{'GEMINI_API_KEY':'test-key'}),patch('try_turn.load_env'),patch('try_turn.urllib.request.urlopen',opener):
            self.assertEqual(ask('Take me to settings',[]),turn)
        self.assertIn('navigate',json.dumps(captured['generationConfig']['responseJsonSchema']))
        self.assertIn('How do I open settings?',SYSTEM)


if __name__ == "__main__":
    unittest.main()
