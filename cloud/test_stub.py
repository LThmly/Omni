"""The offline route never disguises a failed Gemini call as a successful app."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import stub_server

class StubTest(unittest.TestCase):
    def test_offline_navigation_and_message_use_the_same_contract(self):
        with patch.dict(os.environ,{},clear=True),patch('stub_server.try_turn.load_env'):
            turn=stub_server.respond({'text':'Take me to settings','registry':[]})
            self.assertEqual((turn['intent'],turn['destination']),('navigate','settings'))
            turn=stub_server.respond({'text':'How do I open settings?','registry':[]})
            self.assertEqual(turn['intent'],'message');self.assertNotIn('app',turn)
    def test_gemini_failure_is_propagated_without_demo_fallback(self):
        with patch.dict(os.environ,{'GEMINI_API_KEY':'test'},clear=True),patch('stub_server.try_turn.load_env'),patch('stub_server.try_turn.ask',side_effect=stub_server.try_turn.TurnError('failed')):
            with self.assertRaises(stub_server.try_turn.TurnError):stub_server.respond({'text':'Create a list','registry':[]})
    def test_offline_update_targets_typed_shared_state(self):
        registry=[json.loads((Path(__file__).resolve().parents[1]/'contract/fixtures/v2/shopping.json').read_text())]
        with patch.dict(os.environ,{},clear=True),patch('stub_server.try_turn.load_env'):
            turn=stub_server.respond({'text':'Add coffee','registry':registry})
        self.assertEqual(turn['intent'],'update_app');self.assertEqual(turn['app_id'],'shopping')
        self.assertEqual(turn['actions'][1],{'action':'append','target':'items','source':'entry'})

if __name__=='__main__':unittest.main()
