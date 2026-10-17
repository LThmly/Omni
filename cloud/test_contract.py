"""Contract boundaries: reject malformed data and undefined interactions."""
import copy
import json
from pathlib import Path
import unittest
from contract.build_schema import SCHEMAS, MODEL_SCHEMA
from contract.runtime import (ContractError,apply_operations,fields,message,navigation,
                              parse_response,preview_navigation,validate_app,validate_turn)

ROOT=Path(__file__).resolve().parents[1]/'contract'

def fixture(name):return json.loads((ROOT/'fixtures/v2'/name).read_text())

class ContractTest(unittest.TestCase):
    def setUp(self):self.app=fixture('shopping.json')
    def test_generated_schemas_and_all_fixtures_match_the_runtime(self):
        self.assertEqual(json.loads((ROOT/'turn.gemini.json').read_text()),MODEL_SCHEMA)
        for name,schema in SCHEMAS.items():self.assertEqual(json.loads((ROOT/name).read_text()),schema)
        for path in (ROOT/'fixtures/v2').glob('*.json'):
            value=json.loads(path.read_text())
            if 'turn' in value:parse_response(json.dumps(value),[self.app,fixture('counter.json')] if value['turn']['op'] in ('mutate','navigate') else [])
            else:validate_app(value)
    def test_clear_message_and_classified_app_clarification(self):
        turn=message('Hello');self.assertEqual(parse_response(json.dumps({'turn':turn})),turn)
        turn['intent']='create_app';turn['say']='What should the app track?'
        self.assertEqual(validate_turn(turn)['intent'],'create_app')
        turn['app']=self.app
        with self.assertRaises(ContractError):validate_turn(turn)
    def test_rejects_extra_properties_wrong_types_versions_and_intent_mismatches(self):
        turn=fixture('create-shopping.json')['turn']
        cases=[]
        for key,value in [('intent','message'),('schema_version',1),('debug','reasoning'),('say','   ')]:
            bad=copy.deepcopy(turn);bad[key]=value;cases.append(bad)
        bad=copy.deepcopy(turn);bad['app']['state']['fields'][0]['value'][0]['checked']='false';cases.append(bad)
        bad=copy.deepcopy(turn);bad['app']['state']['fields'][0]['value'][0]['onclick']='execute()';cases.append(bad)
        for bad in cases:
            with self.subTest(bad=bad),self.assertRaises(ContractError):validate_turn(bad)
    def test_no_fences_duplicate_properties_trailing_text_or_nonfinite_values(self):
        for text in ('```json\n{}\n```','{} trailing','{"turn":{},"turn":{}}','{"turn":{"x":NaN}}','[]'):
            with self.subTest(text=text),self.assertRaises(ContractError):parse_response(text)
    def test_component_and_action_references_are_closed_and_typed(self):
        cases=[]
        bad=copy.deepcopy(self.app);bad['components'][0]['bind']='missing';cases.append(bad)
        bad=copy.deepcopy(self.app);bad['components'][0]['bind']='entry';cases.append(bad)
        bad=copy.deepcopy(self.app);bad['components'][2]['action']='invented';cases.append(bad)
        bad=copy.deepcopy(self.app);bad['actions'][0]['source']='items';cases.append(bad)
        bad=copy.deepcopy(self.app);bad['components'][0]['type']='webview';cases.append(bad)
        bad=copy.deepcopy(self.app);bad['components'].append(copy.deepcopy(bad['components'][0]));cases.append(bad)
        for bad in cases:
            with self.assertRaises(ContractError):validate_app(bad)
    def test_state_sharing_append_clear_and_updates_persist_data_atomically(self):
        original=copy.deepcopy(self.app)
        updated=apply_operations(self.app,[{'action':'set','target':'entry','value':'Coffee'},
                                          {'action':'append','target':'items','source':'entry'}])
        self.assertEqual(self.app,original)
        self.assertEqual(fields(updated)['items']['value'][-1]['label'],'Coffee')
        self.assertEqual(fields(updated)['entry']['value'],'')
        with self.assertRaises(ContractError):apply_operations(self.app,[{'action':'clear','target':'items'},{'action':'clear','target':'missing'}])
        self.assertEqual(self.app,original)
    def test_number_bounds_and_wrong_action_types(self):
        app=fixture('hydration.json')
        updated=apply_operations(app,[{'action':'increment','target':'value','amount':1000}])
        self.assertEqual(fields(updated)['value']['value'],fields(updated)['value']['max'])
        for operation in ({'action':'set','target':'value','value':True},{'action':'set','target':'value','value':-1},
                          {'action':'increment','target':'value','amount':float('inf')}, {'action':'toggle','target':'value'}):
            with self.assertRaises(ContractError):apply_operations(app,[operation])
    def test_unknown_or_reserved_apps_and_item_id_collisions_rejected(self):
        turn=fixture('create-shopping.json')['turn']
        with self.assertRaises(ContractError):validate_turn(turn,[self.app])
        turn['app']['id']='settings'
        with self.assertRaises(ContractError):validate_turn(turn)
        app=copy.deepcopy(self.app);app['state']['fields'][0]['value'].append(copy.deepcopy(app['state']['fields'][0]['value'][0]))
        with self.assertRaises(ContractError):validate_app(app)
        update=fixture('update-shopping.json')['turn']
        with self.assertRaises(ContractError):validate_turn(update,[])
    def test_navigation_only_uses_known_pages_or_existing_generated_apps(self):
        for destination in ('agent','apps','settings','notes','clock','calculator'):
            self.assertEqual(validate_turn(navigation(destination))['intent'],'navigate')
        validate_turn(navigation('app','shopping'),[self.app])
        for bad in (navigation('browser'),navigation('app','missing'),navigation('settings','shopping')):
            with self.assertRaises(ContractError):validate_turn(bad,[self.app])
    def test_local_navigation_phrases_are_complete_and_unambiguous(self):
        for text,destination in [('Navigate to the settings page','settings'),
                                 ('Please open my notes app','notes'),
                                 ('Hey Omni can you take me to the main agent view please','agent'),
                                 ('Go back to the app selection screen','apps'),
                                 ('Switch to calculator','calculator')]:
            self.assertEqual(preview_navigation(text)['destination'],destination)
        for text in ('How do I navigate to settings?', 'Open settings and change the theme',
                     'Show me how to use notes', 'Open clock or calculator',
                     'Open a new shopping app', 'Navigate to an unknown page'):
            self.assertIsNone(preview_navigation(text,[self.app]))
        duplicate=dict(self.app,id='another_list')
        self.assertIsNone(preview_navigation('Open shopping',[self.app,duplicate]))

    def test_preview_navigation_distinguishes_questions_and_generation(self):
        self.assertEqual(preview_navigation('Take me to settings')['destination'],'settings')
        self.assertEqual(preview_navigation('Take me to the main agent view')['destination'],'agent')
        self.assertIsNone(preview_navigation('How do I open settings?'))
        self.assertIsNone(preview_navigation('Create a settings shortcut app'))
        self.assertEqual(preview_navigation('Open shopping',[self.app])['app_id'],'shopping')

if __name__=='__main__':unittest.main()
