"""Local matching stays explicit, deterministic, contract-valid, and offline."""
import copy
import datetime
import json
from pathlib import Path
import unittest
from local_commands import match_command, spoken_expression, calculate
from native_ui import DEFAULTS, default_apps
from contract.runtime import validate_turn, apply_operations, fields

FIXTURES=Path(__file__).resolve().parents[1]/'contract/fixtures/v2'


class LocalCommandTest(unittest.TestCase):
    def setUp(self):
        self.prefs=DEFAULTS.copy();self.registry=default_apps()
        self.registry += [json.loads((FIXTURES/name).read_text()) for name in ('counter.json','shopping.json')]

    def match(self,text):
        result=match_command(text,self.prefs,self.registry,datetime.datetime(2026,10,17,15,7))
        self.assertIsNotNone(result,text)
        validate_turn(result.turn,self.registry)
        return result

    def test_navigation_phrase_matrix(self):
        verbs=['open','open up','launch','start','load','bring up','pull up','go to','go into',
               'head to','jump to','navigate to','take me to','bring me to','get me to',
               'show me','return to','switch to','switch over to']
        targets={'settings':'settings','preferences':'settings','device settings':'settings',
                 'notebook':'notes','notepad':'notes','digital clock':'clock','calc':'calculator',
                 'main agent':'agent','assistant':'agent','app drawer':'apps','all apps':'apps','app wheel':'apps'}
        for verb in verbs:
            for alias,destination in targets.items():
                phrase='Could you please '+verb+' the '+alias+' page for me'
                with self.subTest(phrase=phrase):
                    self.assertEqual(self.match(phrase).turn['destination'],destination)
        for phrase in ('back','go back','close this app','exit app'):
            self.assertEqual(self.match(phrase).turn['destination'],'apps')
        self.assertEqual(self.match('Please pull up my counter application').turn['app_id'],'simple_counter')

    def test_display_preferences(self):
        cases={'turn animations off':('motion',False),'enable motion effects':('motion',True),
               'turn on reduced motion':('motion',False),'turn off reduced motion':('motion',True),
               'make the font bigger':('text_scale',1.15),'reset text size':('text_scale',1),
               'use military time':('clock24',True),'disable military time':('clock24',False),
               'switch to twelve hour clock':('clock24',False),
               'set the clock to twenty four hour format':('clock24',True),
               'set the preview delay to three seconds':('wait_seconds',3),
               'change demo wait to twenty seconds':('wait_seconds',20),
               'change the system color scheme to light':('theme','light'),
               'turn dark mode off':('theme','light'),
               'turn on night mode':('theme','dark'),'enable day mode':('theme','light'),
               'toggle time format':('clock24',False)}
        for phrase,(key,value) in cases.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.match(phrase).effect,dict(kind='preference',key=key,value=value))
        self.assertEqual(self.prefs,DEFAULTS)

    def test_time_and_date_answers_use_the_device_clock(self):
        self.assertEqual(self.match("What's the current time?").turn['say'],'It is 15:07.')
        self.prefs['clock24']=False
        self.assertEqual(self.match('Tell me the time').turn['say'],'It is 03:07 PM.')
        self.assertEqual(self.match("What's today's date?").turn['say'],'Today is Saturday, October 17, 2026.')

    def test_spoken_arithmetic_and_unsupported_math(self):
        cases={'What is two plus two?':'4','Calculate twenty five times four':'100',
               'Compute one hundred and two divided by three':'34',
               'Work out negative five plus seven':'2',
               'Calculate one point five times two':'3',
               "What's four plus five?":'9','Calculate 12 / (2 + 4)':'2' }
        for phrase,answer in cases.items():
            with self.subTest(phrase=phrase):self.assertEqual(self.match(phrase).effect['value'],answer)
        self.assertIn('undefined',self.match('Calculate two divided by zero').turn['say'])
        for phrase in ('Calculate one two plus three','Calculate 2 ** 100000','Calculate sqrt 9',
                       'What is the weather','What is two plus two and open notes'):
            self.assertIsNone(match_command(phrase,self.prefs,self.registry),phrase)

    def test_notes_capture_preserves_content_and_reading(self):
        result=self.match('Please take a note that Buy Milk, Eggs & Bread.')
        self.assertEqual(result.effect,dict(kind='note',text='Buy Milk, Eggs & Bread.'))
        self.assertIn('empty',self.match('Read my notes').turn['say'])
        self.registry[2]['state']['text']='A'*1500
        self.assertIn('see the rest',self.match('Read my notes').turn['say'])
        self.assertLessEqual(len(self.match('Read my notes').turn['say']),1200)

    def test_generated_actions_use_only_declared_operations(self):
        before=copy.deepcopy(self.registry)
        result=self.match('Press the increase button in my counter app')
        app=self.registry[-2]
        updated=apply_operations(app,result.turn['actions'])
        self.assertEqual(fields(updated)['count']['value'],1)
        result=self.match('Add Milk and Eggs to my shopping list')
        updated=apply_operations(self.registry[-1],result.turn['actions'])
        self.assertEqual(fields(updated)['items']['value'][-1]['label'],'Milk and Eggs')
        self.assertEqual(self.registry,before)
        self.assertIsNone(match_command('Press the delete everything button in counter',self.prefs,self.registry))
        self.registry.append(dict(copy.deepcopy(app),id='counter_two'))
        self.assertIsNone(match_command('Run reset in counter',self.prefs,self.registry))

    def test_list_limits_return_a_clear_local_error_without_changes(self):
        app=self.registry[-1]
        fields(app)['items']['value']=[dict(id='item_'+str(i),label='Item',checked=False) for i in range(100)]
        before=copy.deepcopy(app)
        result=self.match('Add Milk to shopping')
        self.assertEqual(result.turn['op'],'say')
        self.assertIn('full',result.turn['say'])
        self.assertEqual(app,before)

    def test_questions_negations_unknown_and_multiple_tasks_fall_through(self):
        for phrase in ('How do I disable animations?','Do not turn off animations','Could you not open notes',
                       'Change the theme and open notes','Open settings and turn on dark mode',
                       'What is a calculator','Create a notebook app','Remind me tomorrow',
                       'Set a timer for ten minutes','Set brightness to 80 percent',
                       'Enable wifi','Open missing app','Use 13 hour time',
                       'Switch to light mode or dark mode','Make the font bigger and open clock'):
            with self.subTest(phrase=phrase):
                self.assertIsNone(match_command(phrase,self.prefs,self.registry))
