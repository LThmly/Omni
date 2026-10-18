"""Exercise the same pygame flow used by desktop simulator and Pi kiosk."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ['OMNI_SPEAK']='0'
import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import pygame
from native_ui import NativeApp, PartialSpeechDemo, calculate, default_apps, VOICE, theme_command
from phone import Hit, phone_point, screen_point
from contract.runtime import message, navigation, fields, validate_app
from contract.legacy import to_composed


class NativeUITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store=Path(self.temp.name)/'registry.json'
        recorder_patch=patch('native_ui.legacy.AudioRecorder')
        recorder=recorder_patch.start().return_value
        recorder.stop.return_value=None
        self.addCleanup(recorder_patch.stop)
        self.app=NativeApp('http://unused','none',False,self.store)
        self.addCleanup(self.app.close)
        self.ticks=1000
        self.paint()

    def paint(self,delta=0):
        self.ticks+=delta
        self.app.screen.paint(self.app.phone,self.app.device,self.ticks,self.app.draft)

    def activate(self,action,**kwargs):
        self.app.activate(Hit((0,0,1,1),action,**kwargs));self.paint(600)
        if self.app.screen.page_transition:self.paint(400)

    def open(self,id):
        self.app.screen.transition=None
        self.app.screen.last_view='arc'
        self.activate('open',app_id=id)

    def key(self,key,mod=0):
        return self.app.on_key(pygame.event.Event(pygame.KEYDOWN,key=key,mod=mod))

    def test_five_defaults_and_no_talk_on_wheel(self):
        self.assertEqual([a['id'] for a in self.app.device.registry],['omni','settings','notes','clock','calculator'])
        self.assertEqual([h.act for h in self.app.screen.hits if h.act=='talk'],['talk'])
        self.activate('launcher');self.paint(600)
        self.assertTrue(self.app.screen.launcher)
        self.assertFalse(any(h.act=='talk' for h in self.app.screen.hits))
        self.assertEqual(len([h for h in self.app.screen.hits if h.act in ('open','select')]),5)

    def test_transition_and_reduced_motion(self):
        self.app.set_launcher(True);self.paint()
        self.assertIsNotNone(self.app.screen.transition)
        self.paint(240)
        self.assertAlmostEqual(self.app.screen.transition_value,.5)
        self.paint(240)
        self.assertIsNone(self.app.screen.transition)
        self.app.set_launcher(False);self.paint();self.paint(240)
        self.assertAlmostEqual(self.app.screen.transition_value,.5)
        self.paint(240)
        self.app.prefs['motion']=False
        self.app.set_launcher(True);self.paint()
        self.assertIsNone(self.app.screen.transition)

    def test_app_slide_blocks_input_and_returns_to_same_wheel_position(self):
        self.app.set_launcher(True);self.paint();self.paint(500)
        self.app.screen.wheel_to(1);self.paint(500)
        self.app.activate(Hit((0,0,1,1),'open',app_id='settings'));self.paint()
        self.assertIsNotNone(self.app.screen.page_transition)
        self.assertEqual(self.app.screen.hits,[])
        self.app.activate(Hit((0,0,1,1),'setting',index=0))
        self.assertEqual(self.app.prefs['theme'],'dark')
        self.paint(180)
        self.assertIsNotNone(self.app.screen.page_transition)
        self.paint(180)
        self.assertFalse(self.app.screen.busy)
        self.app.set_launcher(True);self.paint();self.paint(360)
        self.assertEqual(self.app.screen.selection,1)
        self.assertTrue(any(h.act=='open' and h.app_id=='settings' for h in self.app.screen.hits))

    def test_voice_navigation_waits_for_wheel_rotates_then_opens(self):
        self.app.navigate_app('calculator');self.paint()
        self.assertEqual(self.app.screen.position,1)
        self.app.poll()
        self.assertEqual(self.app.screen.navigation['stage'],'arrive')
        self.assertIsNone(self.app.device.current())
        self.paint(480);self.app.poll()
        self.assertEqual(self.app.screen.target,-1)
        self.assertEqual(self.app.screen.navigation['stage'],'rotate')
        self.paint(500);self.app.poll()
        self.assertEqual(self.app.screen.selection%5,4)
        self.assertIsNone(self.app.device.current())
        self.paint(120);self.app.poll();self.paint()
        self.assertEqual(self.app.device.current()['id'],'calculator')
        self.assertIsNotNone(self.app.screen.page_transition)
        self.paint(360);self.assertFalse(self.app.screen.busy)

    def test_navigation_cancel_and_reduced_motion(self):
        self.app.navigate_app('settings');self.key(pygame.K_ESCAPE)
        self.assertIsNone(self.app.screen.navigation)
        self.settle_navigation()
        self.assertIsNone(self.app.device.current())
        self.app.prefs['motion']=False
        self.app.navigate_app('clock');self.paint()
        self.assertEqual(self.app.device.current()['id'],'clock')
        self.assertFalse(self.app.screen.busy)

    def test_rotational_drag_snaps_and_wraps(self):
        self.app.prefs['motion']=False
        self.activate('launcher')
        self.app.on_down((236,467))
        self.app.on_move((300,578))
        self.assertNotEqual(self.app.screen.position,0)
        self.app.on_up((300,578))
        self.assertEqual(self.app.screen.position,round(self.app.screen.position))
        self.app.scroll_input(-8);self.paint()
        self.key(pygame.K_RETURN)
        expected=self.app.device.registry[round(self.app.screen.target)%5]['id']
        if expected=='omni':self.assertFalse(self.app.screen.launcher)
        else:self.assertEqual(self.app.device.app_id,expected)

    def test_hold_cancel_and_generated_app_selected_after_wait(self):
        self.app.on_down(VOICE.center)
        self.assertEqual(self.app.device.agent,'listening')
        self.app.cancel_press()
        self.assertEqual(self.app.device.agent,'idle')
        with patch('pygame.time.get_ticks',side_effect=[1000,1400]):
            self.app.on_down(VOICE.center);self.app.on_up(VOICE.center)
        self.assertEqual(self.app.device.agent,'thinking')
        due=self.app.pending['due']
        self.assertAlmostEqual(due, __import__('time').monotonic()+10,delta=.1)
        with patch('native_ui.time.monotonic',return_value=due-.1):self.app.poll()
        self.assertEqual(len(self.app.device.registry),5)
        with patch('native_ui.time.monotonic',return_value=due+.1):self.app.poll()
        self.finish_response()
        self.assertEqual(len(self.app.device.registry),6)
        self.assertEqual(self.app.device.agent,'idle')
        self.assertTrue(self.app.screen.launcher)
        self.assertEqual(self.app.device.registry[self.app.screen.selection]['id'],'shopping')
        self.paint();self.assertIsNotNone(self.app.screen.transition)

    def test_settings_notes_and_clock_persist_with_touch_keyboard(self):
        self.open('settings');self.activate('setting',index=0)
        self.assertEqual(self.app.prefs['theme'],'light')
        self.assertEqual(self.app.phone.get_at((5,5))[:3],(255,255,255))
        self.activate('setting',index=2);self.activate('setting',index=3)
        self.open('notes');self.activate('edit_notes')
        self.activate('key',text='hello');self.activate('key',text='newline');self.activate('key',text='world')
        self.activate('key',text='done')
        self.assertEqual(self.app.device.find('notes')['state']['text'],'hello\nworld')
        self.open('clock');self.activate('clock_format')
        restored=NativeApp('http://unused','none',False,self.store)
        self.assertEqual(restored.device.find('notes')['state']['text'],'hello\nworld')
        self.assertEqual(restored.prefs['theme'],'light')
        self.assertEqual(restored.prefs['text_scale'],1.15)
        self.assertEqual(restored.prefs['wait_seconds'],20)
        self.assertFalse(restored.prefs['clock24'])
        self.assertIsNone(restored.device.current())
        self.app.prefs['theme']='dark';self.paint()

    def test_calculator_and_back_navigation(self):
        self.open('calculator')
        for key in ['2','+','3','×','4','=']:self.activate('calc',text=key)
        self.assertEqual(self.app.screen.calculator,'14')
        self.activate('calc',text='C');self.app.on_text('1/0');self.key(pygame.K_RETURN)
        self.assertEqual(self.app.screen.calculator,'Error')
        self.key(pygame.K_ESCAPE);self.paint(600);self.paint(600)
        self.assertIsNone(self.app.device.current());self.assertTrue(self.app.screen.launcher)
        self.key(pygame.K_ESCAPE);self.assertFalse(self.app.screen.launcher)

    def test_touch_back_tolerates_finger_drift_on_all_app_pages(self):
        generated=self.fixture('shopping.json');self.app.select_app(generated)
        for app_id in ('settings','notes','clock','calculator',generated['id']):
            with self.subTest(app_id=app_id):
                self.open(app_id)
                hit=next(h for h in self.app.screen.hits if h.act=='back')
                x,y=hit.rect.center
                self.app.on_down((x,y));self.app.on_move((x+9,y+7));self.app.on_up((x+9,y+7))
                self.assertIsNone(self.app.device.current())
                self.assertTrue(self.app.screen.launcher)
                self.paint();self.paint(400)

    def test_touch_back_cancelled_when_drag_leaves_button(self):
        self.open('settings')
        hit=next(h for h in self.app.screen.hits if h.act=='back')
        x,y=hit.rect.center
        self.app.on_down((x,y));self.app.on_move((x-100,y+100));self.app.on_up((x,y))
        self.assertEqual(self.app.device.current()['id'],'settings')

    def test_touch_settings_back_row_tolerates_finger_drift(self):
        self.open('settings')
        hit=next(h for h in self.app.screen.hits if h.act=='setting' and h.index==4)
        x,y=hit.rect.center
        self.app.on_down((x,y));self.app.on_move((x+10,y+8));self.app.on_up((x+10,y+8))
        self.assertIsNone(self.app.device.current())

    def touch(self,hit,dx=10,dy=8):
        x,y=hit.rect.center
        self.app.on_down((x,y));self.app.on_move((x+dx,y+dy))
        self.paint()  # The real loop rebuilds all hit objects between events.
        self.app.on_up((x+dx,y+dy));self.paint()

    def test_settings_calculator_clock_and_keyboard_tolerate_touch_drift(self):
        self.open('settings')
        self.touch(next(h for h in self.app.screen.hits if h.act=='setting' and h.index==0))
        self.assertEqual(self.app.prefs['theme'],'light')
        self.assertEqual(self.app.screen.scroll,0)
        self.open('calculator')
        self.touch(next(h for h in self.app.screen.hits if h.act=='calc' and h.text=='7'))
        self.assertEqual(self.app.screen.calculator,'7')
        self.open('clock')
        self.touch(next(h for h in self.app.screen.hits if h.act=='clock_format'))
        self.assertFalse(self.app.prefs['clock24'])
        self.open('notes')
        self.touch(next(h for h in self.app.screen.hits if h.act=='edit_notes'))
        self.assertIsNotNone(self.app.screen.keyboard)
        self.touch(next(h for h in self.app.screen.hits if h.act=='key' and h.text=='a'))
        self.assertEqual(self.app.device.find('notes')['state']['text'],'a')
        self.touch(next(h for h in self.app.screen.hits if h.act=='key' and h.text=='done'))
        self.assertIsNone(self.app.screen.keyboard)

    def test_release_over_neighbor_never_activates_either_calculator_key(self):
        self.open('calculator')
        first=next(h for h in self.app.screen.hits if h.act=='calc' and h.text=='7')
        other=next(h for h in self.app.screen.hits if h.act=='calc' and h.text=='8')
        self.app.on_down(first.rect.center)
        # Even when the driver delivers no intervening motion event.
        self.app.on_up(other.rect.center)
        self.assertEqual(self.app.screen.calculator,'')

    def test_keyboard_drag_cancels_instead_of_typing_neighbor(self):
        self.open('notes');self.activate('edit_notes')
        first=next(h for h in self.app.screen.hits if h.act=='key' and h.text=='a')
        other=next(h for h in self.app.screen.hits if h.act=='key' and h.text=='s')
        self.app.on_down(first.rect.center);self.app.on_move(other.rect.center)
        self.app.on_up(other.rect.center)
        self.assertEqual(self.app.device.find('notes')['state']['text'],'')

    def test_component_taps_tolerate_drift_but_scroll_does_not_toggle_items(self):
        app=self.fixture('shopping.json')
        fields(app)['items']['value']=[dict(id=f'item_{i}',label=f'Item {i}',checked=False) for i in range(20)]
        self.app.select_app(app);self.open(app['id'])
        item=next(h for h in self.app.screen.hits if h.act=='component_item')
        self.touch(item)
        self.assertTrue(fields(app)['items']['value'][0]['checked'])
        item=next(h for h in self.app.screen.hits if h.act=='component_item' and h.index==2)
        x,y=item.rect.center
        self.app.on_down((x,y));self.app.on_move((x,y-90));self.paint();self.app.on_up((x,y-90))
        self.assertEqual(self.app.screen.scroll,90)
        self.assertFalse(fields(app)['items']['value'][2]['checked'])
        self.assertFalse(fields(app)['items']['value'][3]['checked'])

    def test_component_buttons_and_inputs_tolerate_drift(self):
        app=self.fixture('shopping.json');self.app.select_app(app);self.open(app['id'])
        self.touch(next(h for h in self.app.screen.hits if h.act=='component_input'))
        self.app.keyboard_key('Eggs');self.app.keyboard_key('done');self.paint()
        self.touch(next(h for h in self.app.screen.hits if h.act=='component_action' and h.text=='append_item'))
        self.assertEqual(fields(app)['items']['value'][-1]['label'],'Eggs')

    def test_wheel_tap_drift_does_not_start_rotation(self):
        self.app.prefs['motion']=False
        self.app.set_launcher(True);self.paint()
        hit=next(h for h in self.app.screen.hits if h.act=='select' and h.app_id=='settings')
        self.touch(hit,dx=8,dy=6)
        self.assertEqual(self.app.screen.selection%5,1)
        self.assertEqual(self.app.screen.position,round(self.app.screen.position))

    def test_returning_to_omni_clears_previous_response_and_text_animation(self):
        self.app.prefs['motion']=False
        for entry in ('logo','open','escape','voice'):
            with self.subTest(entry=entry):
                self.app.device.say='Previous response'
                self.paint()
                self.assertEqual(self.app.screen.transcript.text,'Previous response')
                self.app.set_launcher(True);self.paint()
                if entry=='logo':self.activate('logo')
                elif entry=='open':self.activate('open',app_id='omni')
                elif entry=='escape':self.key(pygame.K_ESCAPE)
                else:self.deliver(navigation('agent'))
                self.paint()
                self.assertEqual(self.app.device.say,'')
                self.assertEqual(self.app.screen.transcript.text,'')
                self.assertIsNone(self.app.device.current())
                self.assertFalse(self.app.screen.launcher)

    def test_local_navigation_bypasses_gemini_after_final_asr(self):
        speech=Mock();speech.start.return_value=42;speech.poll.return_value=[]
        self.app.speech=speech;self.app.backend='gemini';self.app.live=True
        with patch('pygame.time.get_ticks',side_effect=[1000,1600]):
            self.app.on_down(VOICE.center);self.app.on_up(VOICE.center)
        speech.poll.return_value=[(42,'final',{'text':'Navigate to the settings page'})]
        with patch('threading.Thread') as thread:
            self.app.poll()
            thread.assert_not_called()
        self.assertIsNone(self.app.pending)
        self.assertEqual(self.app.after_response['destination'],'settings')
        self.assertEqual(self.app.device.last_turn['intent'],'navigate')
        speech.poll.return_value=[]
        self.settle_navigation()
        self.assertEqual(self.app.device.current()['id'],'settings')

    def test_uncertain_navigation_still_uses_gemini(self):
        self.app.backend='gemini';self.app.live=True
        with patch('threading.Thread') as thread:
            self.app.send('Open settings and change the theme')
            thread.assert_called_once()
        self.assertIsNotNone(self.app.pending)
        self.assertTrue(self.app.events.empty())

    def test_voice_wheel_starts_maximally_far_for_odd_and_even_app_counts(self):
        for extra in (False,True):
            if extra:self.app.select_app(self.fixture('shopping.json'))
            n=len(self.app.device.registry)
            for target,app in enumerate(self.app.device.registry[1:],start=1):
                self.app.navigate_app(app['id'])
                start=self.app.screen.selection
                distance=min((target-start)%n,(start-target)%n)
                self.assertEqual(distance,n//2)
                self.app.screen.navigation=None

    def test_navigation_response_finishes_drawing_and_holds_before_wheel(self):
        self.app.backend='gemini';self.app.live=True
        with patch('threading.Thread') as thread:
            self.app.send('Navigate to the settings page');self.app.poll()
            thread.assert_not_called()
        self.assertEqual(self.app.device.say,'Opening settings.')
        self.assertIsNone(self.app.screen.navigation)
        self.assertFalse(self.app.screen.launcher)
        # Backend completion alone, without any rendered frame, cannot navigate.
        for _ in range(3):self.app.poll()
        self.assertIsNotNone(self.app.after_response)
        self.paint()
        self.assertEqual(self.app.screen.transcript.text,'Opening')
        self.paint(50)
        self.assertEqual(self.app.screen.transcript.text,'Opening settings.')
        self.app.poll();self.assertIsNone(self.app.response_ready_at)
        self.paint(300);self.app.poll()
        ready=self.app.response_ready_at
        self.assertIsNotNone(ready)
        self.paint(1199);self.app.poll()
        self.assertFalse(self.app.screen.launcher)
        self.paint(1);self.app.poll()
        self.assertTrue(self.app.screen.launcher)
        self.assertEqual(self.app.screen.navigation['app_id'],'settings')
        self.settle_navigation()
        self.assertEqual(self.app.device.current()['id'],'settings')

    def test_app_creation_waits_for_response_and_escape_can_cancel_action(self):
        self.app.backend='gemini';self.app.live=True
        with patch('threading.Thread'):self.app.send('Create a counter')
        turn=self.fixture('create-counter.json')['turn']
        self.app.events.put((self.app.pending['number'],turn));self.app.poll();self.paint()
        self.assertEqual(len(self.app.device.registry),5)
        self.assertEqual(self.app.device.say,turn['say'])
        self.assertIsNotNone(self.app.after_response)
        self.key(pygame.K_ESCAPE)
        self.settle_navigation()
        self.assertEqual(len(self.app.device.registry),5)
        self.assertIsNone(self.app.after_response)

    def test_partial_transcription_revisions_render_and_stay_during_backend_wait(self):
        self.app.on_down(VOICE.center)
        self.app.apply_speech_result({'partial':'take me to the clock'})
        self.paint();self.paint(250)
        self.assertEqual(self.app.screen.transcript.text,'take me to the clock')
        self.app.apply_speech_result({'partial':'take me to the calculator'})
        self.paint();self.paint(250)
        self.assertEqual(self.app.screen.transcript.text,'take me to the calculator')
        old=self.app.screen.transcript.words[0]
        self.app.backend='gemini';self.app.live=True
        with patch('threading.Thread'):self.app.send('take me to the calculator')
        self.paint()
        self.assertEqual(self.app.screen.transcript.text,'take me to the calculator')
        self.assertIs(self.app.screen.transcript.words[0],old)

    def test_reduced_motion_still_shows_response_before_action(self):
        self.app.prefs['motion']=False
        self.app.send('Navigate to settings');self.app.poll();self.paint();self.app.poll()
        self.assertEqual(self.app.screen.transcript.text,'Opening settings.')
        self.assertIsNone(self.app.device.current())
        self.paint(1199);self.app.poll()
        self.assertIsNone(self.app.device.current())
        self.paint(1);self.app.poll()
        self.assertEqual(self.app.device.current()['id'],'settings')

    def test_local_theme_phrases_are_explicit(self):
        for phrase,target in [('Switch to light mode','light'),('Enable dark mode','dark'),
                              ('Please set the theme to light mode','light'),
                              ('Hey Omni change system color scheme to dark mode please','dark'),
                              ('Turn on light mode','light'),('Use dark theme','dark'),
                              ('Can you switch to light mode','light'),('dark mode','dark')]:
            with self.subTest(phrase=phrase):self.assertEqual(theme_command(phrase,'dark'),target)
        self.assertEqual(theme_command('Toggle the color scheme','dark'),'light')
        self.assertEqual(theme_command('Switch between light and dark mode','light'),'dark')
        for phrase in ('What is dark mode','Switch to light mode and open settings',
                       'Create a dark mode app','Do not enable dark mode','Open settings'):
            self.assertIsNone(theme_command(phrase,'dark'))

    def test_voice_theme_change_skips_api_waits_for_response_and_persists(self):
        self.app.backend='gemini';self.app.live=True
        with patch('threading.Thread') as thread:
            self.app.send('Switch to light mode');self.app.poll()
            thread.assert_not_called()
        self.assertEqual(self.app.prefs['theme'],'dark')
        self.assertEqual(self.app.device.say,'Switching to light mode.')
        self.finish_response();self.paint()
        self.assertEqual(self.app.prefs['theme'],'light')
        self.assertEqual(json.loads(self.app.preferences_path.read_text())['theme'],'light')
        self.assertEqual(self.app.phone.get_at((0,0))[:3],(255,255,255))
        self.assertFalse(self.app.screen.launcher)
        self.assertIsNone(self.app.device.current())
        self.app.send('Switch to dark mode');self.app.poll();self.finish_response();self.paint()
        self.assertEqual(self.app.prefs['theme'],'dark')
        self.assertEqual(self.app.phone.get_at((0,0))[:3],(0,0,0))

    def test_theme_command_works_offline_and_escape_cancels_it(self):
        self.app.send('Enable light mode');self.app.poll()
        self.assertEqual(self.app.device.say,'Switching to light mode.')
        self.key(pygame.K_ESCAPE);self.settle_navigation()
        self.assertEqual(self.app.prefs['theme'],'dark')
        self.assertIsNone(self.app.deferred_effect)
        self.app.send('Toggle the theme');self.app.poll();self.finish_response()
        self.assertEqual(self.app.prefs['theme'],'light')

    def test_expanded_local_preferences_apply_after_response_and_persist(self):
        self.app.backend='gemini';self.app.live=True
        for phrase,key,value in [('Make the font bigger','text_scale',1.15),
                                 ('Use twelve hour time','clock24',False),
                                 ('Set preview wait to three seconds','wait_seconds',3),
                                 ('Turn animations off','motion',False)]:
            with self.subTest(phrase=phrase),patch('threading.Thread') as thread:
                self.app.send(phrase);self.app.poll()
                thread.assert_not_called()
                self.assertIsNotNone(self.app.after_response)
                self.finish_response()
                self.assertEqual(self.app.prefs[key],value)
                self.assertEqual(json.loads(self.app.preferences_path.read_text())[key],value)

    def test_local_note_capture_and_calculation_keep_response_before_action(self):
        self.app.backend='gemini';self.app.live=True
        with patch('threading.Thread') as thread:
            self.app.send('Take a note that Buy Milk');self.app.poll()
            self.assertEqual(self.app.device.find('notes')['state']['text'],'')
            self.finish_response();self.settle_navigation()
            self.assertEqual(self.app.device.current()['id'],'notes')
            self.assertEqual(self.app.device.find('notes')['state']['text'],'Buy Milk')
            self.app.send('Calculate twenty five times four');self.app.poll()
            self.assertEqual(self.app.device.say,'The answer is 100.')
            self.assertEqual(self.app.screen.calculator,'')
            self.finish_response();self.settle_navigation()
            self.assertEqual(self.app.screen.calculator,'100')
            self.assertEqual(self.app.device.current()['id'],'calculator')
            thread.assert_not_called()

    def test_local_generated_actions_apply_after_ack_without_api(self):
        counter=self.fixture('counter.json');self.app.select_app(counter)
        self.app.backend='gemini';self.app.live=True
        with patch('threading.Thread') as thread:
            self.app.send('Press the increase button in counter');self.app.poll()
            self.assertEqual(fields(counter)['count']['value'],0)
            self.assertEqual(self.app.device.last_turn['op'],'mutate')
            self.finish_response()
            self.assertEqual(fields(counter)['count']['value'],1)
            thread.assert_not_called()

    def test_arithmetic_rejects_code_and_supports_negation(self):
        self.assertEqual(calculate('-(2+3)*4'),'-20')
        with self.assertRaises(ValueError):calculate('__import__("os")')
        with self.assertRaises(ValueError):calculate('2**1000000')

    def test_live_reply_selection_and_cancelled_request(self):
        self.app.live=True
        with patch.object(self.app, 'fetch_native'):
            self.app.send('make something')
        pending=self.app.pending
        proposal={'schema_version':2,'intent':'create_app','say':'Your list is ready.','op':'propose','app':{'id':'new_list','title':'New list','module':'checklist',
                  'state':{'cursor':0,'items':[{'label':'Item','checked':False}]}}}
        proposal['app']=to_composed(proposal['app'])
        self.app.events.put((pending['number'],proposal))
        with patch('native_ui.time.monotonic',return_value=pending['due']+1):self.app.poll()
        self.finish_response()
        self.assertEqual(self.app.device.registry[self.app.screen.selection]['id'],'new_list')
        self.assertTrue(self.app.screen.launcher)
        self.app.live=False
        self.app.send('water')
        self.key(pygame.K_ESCAPE)
        self.app.poll()
        self.assertIsNone(self.app.pending)
        self.assertEqual(len(self.app.device.registry),6)
        self.assertEqual(self.app.device.agent,'idle')

    def test_live_request_is_visible_while_held_and_after_submission(self):
        with patch('pygame.time.get_ticks', side_effect=[1000,1500]):
            self.app.on_down(VOICE.center)
            self.app.on_text('Track water')
            self.paint()
            self.assertEqual(self.app.screen.transcript.text,'Track water')
            self.key(pygame.K_BACKSPACE)
            self.assertEqual(self.app.screen.listening_text,'Track wate')
            self.app.on_text('r')
            self.app.on_up(VOICE.center)
        self.assertEqual(self.app.pending['request'],'Track water')
        self.paint()
        self.assertEqual(self.app.screen.transcript.text,'Track water')

    def test_old_input_visibility_setting_does_not_hide_responses(self):
        self.app.preferences_path.write_text('{"show_input": false}')
        restored=NativeApp('http://unused','none',False,self.store)
        self.addCleanup(restored.close)
        self.assertNotIn('show_input',restored.prefs)
        restored.screen.submitted_text='Private request'
        restored.device.say='Here is your response'
        restored.screen.paint(restored.phone,restored.device,1000,'Private request')
        restored.screen.paint(restored.phone,restored.device,1400,'Private request')
        self.assertEqual(restored.screen.transcript.text,'Here is your response')

    def test_response_keeps_latest_lines_and_settings_back_is_accessible(self):
        self.app.device.say='A'*200+' latest words'
        self.paint();self.paint(400);self.paint(400)
        frames=list(self.app.screen.transcript.frames(self.ticks))
        visible=[word for word,x,y,alpha in frames if 0<=y<66 and alpha>0]
        self.assertEqual(visible[-2:],['latest','words'])
        self.assertGreater(self.app.screen.transcript.scroll(self.ticks),0)
        self.open('settings')
        settings=[hit for hit in self.app.screen.hits if hit.act=='setting']
        self.assertEqual(len(settings),5)
        self.assertTrue(all(hit.rect.bottom<800 for hit in settings))
        self.app.screen.setting_cursor=4
        self.app.scroll_input(1)
        self.assertEqual(self.app.screen.setting_cursor,0)
        self.activate('setting',index=4)
        self.assertIsNone(self.app.device.current())
        self.assertTrue(self.app.screen.launcher)

    def test_partial_demo_reveals_words_and_corrects_a_hypothesis(self):
        with patch('pygame.time.get_ticks',return_value=1000):self.app.on_down(VOICE.center)
        preview=self.app.speech_preview
        self.app.update_speech_preview(1000)
        self.assertEqual(self.app.screen.listening_text,'')
        self.app.update_speech_preview(1250)
        self.assertEqual(self.app.screen.listening_text,'add')
        wrong=next(at for at,text in preview.events if text=='add mill')
        corrected=next(at for at,text in preview.events if text=='add milk')
        self.app.update_speech_preview(1000+wrong)
        self.assertEqual(self.app.screen.listening_text,'add mill')
        self.app.update_speech_preview(1000+corrected)
        self.assertEqual(self.app.screen.listening_text,'add milk')
        self.app.update_speech_preview(10000)
        self.assertEqual(self.app.screen.listening_text,'add milk to my shopping list')
        with patch('pygame.time.get_ticks',return_value=10000):self.app.on_up(VOICE.center)
        self.assertEqual(self.app.pending['request'],preview.final_result()['text'])
        self.assertEqual(self.app.screen.submitted_text,preview.final_result()['text'])
        self.app.apply_speech_result({'partial':'late stale result'})
        self.assertNotEqual(self.app.screen.listening_text,'late stale result')

    def test_vosk_shaped_segments_replace_partials_and_keep_committed_words(self):
        self.app.on_down(VOICE.center)
        self.app.speech_preview=None
        self.app.apply_speech_result({'partial':'add mill'})
        self.app.apply_speech_result({'partial':'add milk'})
        self.assertEqual(self.app.screen.listening_text,'add milk')
        self.app.apply_speech_result({'text':'add milk'})
        self.app.apply_speech_result({'partial':'to my'})
        self.app.apply_speech_result({'partial':'to my shopping list'})
        self.assertEqual(self.app.screen.listening_text,'add milk to my shopping list')
        self.app.apply_speech_result({'text':'to my shopping list'})
        self.assertEqual(self.app.screen.listening_text,'add milk to my shopping list')
        self.app.cancel_press()
        self.app.apply_speech_result({'partial':'stale'})
        self.assertEqual(self.app.screen.listening_text,'')

    def test_partial_demo_custom_phrase_is_sent_and_displayed(self):
        self.app.prefs['motion']=False
        self.app.draft='Track my daily water'
        with patch('pygame.time.get_ticks',return_value=1000):self.app.on_down(VOICE.center)
        self.app.update_speech_preview(10000)
        self.assertEqual(self.app.screen.listening_text,'track my daily water')
        with patch.object(self.app.screen,'label',wraps=self.app.screen.label) as label:
            self.paint()
            self.assertEqual(self.app.screen.transcript.text,'track my daily water')
        with patch('pygame.time.get_ticks',return_value=10000):self.app.on_up(VOICE.center)
        self.assertEqual(self.app.pending['request'],'Track my daily water')
        self.assertIsNone(self.app.speech_preview)

    def test_microphone_partial_updates_and_release_uses_real_final_text(self):
        speech=Mock()
        speech.start.return_value=7
        speech.poll.return_value=[]
        self.app.speech=speech
        with patch('pygame.time.get_ticks',side_effect=[1000,1600]):
            self.app.on_down(VOICE.center)
            self.assertIsNone(self.app.speech_preview)
            speech.poll.return_value=[(7,'partial',{'partial':'track wetter'})]
            self.app.poll()
            self.assertEqual(self.app.screen.listening_text,'track wetter')
            speech.poll.return_value=[(7,'partial',{'partial':'track water'})]
            self.app.poll()
            self.assertEqual(self.app.screen.listening_text,'track water')
            self.app.on_up(VOICE.center)
        speech.finish.assert_called_once_with(7)
        self.assertIsNone(self.app.pending)
        self.assertTrue(self.app.speech_finalizing)
        speech.poll.return_value=[(7,'final',{'text':'track my water intake'})]
        self.app.poll()
        self.assertEqual(self.app.pending['request'],'track my water intake')
        self.assertIsNone(self.app.speech_session)
        self.assertFalse(self.app.speech_finalizing)

    def test_microphone_cancel_and_silence_do_not_generate_default_app(self):
        speech=Mock();speech.start.return_value=8;speech.poll.return_value=[]
        self.app.speech=speech
        self.app.on_down(VOICE.center);self.app.cancel_press()
        speech.cancel.assert_called_once_with(8)
        speech.poll.return_value=[(8,'final',{'text':'late result'})]
        self.app.poll()
        self.assertIsNone(self.app.pending)
        speech.poll.return_value=[]
        with patch('pygame.time.get_ticks',side_effect=[1000,1600]):
            self.app.on_down(VOICE.center);self.app.on_up(VOICE.center)
        speech.poll.return_value=[(8,'final',{'text':''})]
        self.app.poll()
        self.assertIsNone(self.app.pending)
        self.assertEqual(len(self.app.device.registry),5)
        self.assertIn('No speech detected',self.app.device.say)

    def test_only_response_is_visible_when_agent_returns_idle(self):
        self.app.screen.submitted_text='Create a note taking app'
        self.app.device.agent='idle'
        self.app.draft=''
        self.paint()
        self.assertEqual(self.app.screen.transcript.text,'')
        self.app.device.say='Your app is ready'
        self.paint();self.paint(400)
        self.assertEqual(self.app.screen.transcript.text,'Your app is ready')
        self.app.on_down(VOICE.center)
        self.assertEqual(self.app.screen.submitted_text,'')
        self.paint()
        self.assertEqual(self.app.screen.transcript.text,'')

    def test_direct_gemini_reply_creates_and_selects_app_through_shared_flow(self):
        self.app.backend='gemini';self.app.live=True
        proposal={'schema_version':2,'intent':'create_app','say':'Your list is ready.','op':'propose','app':{'id':'voice_list','title':'Voice list','module':'checklist',
                  'state':{'cursor':0,'items':[{'label':'Milk','checked':False}]}}}
        proposal['app']=to_composed(proposal['app'])
        with patch('threading.Thread') as worker:
            self.app.send('Create a shopping list')
        payload,number=worker.call_args.kwargs['args']
        self.assertEqual(payload['registry'],[])
        with patch('cloud.try_turn.ask',return_value=proposal) as ask:
            self.app.fetch_native(payload,number)
        ask.assert_called_once_with('Create a shopping list',[],wav_base64=None)
        with patch('native_ui.time.monotonic',return_value=self.app.pending['due']+1):self.app.poll()
        self.finish_response()
        self.assertTrue(self.app.screen.launcher)
        self.assertEqual(self.app.device.registry[self.app.screen.selection]['id'],'voice_list')

    def test_direct_gemini_errors_are_visible_and_keep_transcript(self):
        from cloud.try_turn import TurnError
        self.app.backend='gemini';self.app.live=True
        with patch('threading.Thread') as worker:self.app.send('Make a timer')
        payload,number=worker.call_args.kwargs['args']
        with patch('cloud.try_turn.ask',side_effect=TurnError('Could not reach Gemini.')):
            self.app.fetch_native(payload,number)
        with patch('native_ui.time.monotonic',return_value=self.app.pending['due']+1):self.app.poll()
        self.assertEqual(self.app.device.say,'Could not reach Gemini.')
        self.assertEqual(self.app.screen.submitted_text,'Make a timer')
        self.assertEqual(len(self.app.device.registry),5)

    def test_real_backend_wait_animation_tracks_response_not_preview_timer(self):
        self.app.backend='gemini';self.app.live=True
        with patch('native_ui.time.monotonic',return_value=100),patch('threading.Thread'):
            self.app.send('Hello')
        with patch('native_ui.time.monotonic',return_value=100.1):self.app.poll()
        self.assertEqual(self.app.device.agent,'thinking')
        self.app.events.put((self.app.pending['number'],message('Hello!')))
        with patch('native_ui.time.monotonic',return_value=100.2):self.app.poll()
        self.assertIsNone(self.app.pending)
        self.assertEqual(self.app.device.agent,'idle')
        self.assertEqual(self.app.device.say,'Hello!')

    def test_demo_keeps_configured_preview_wait(self):
        with patch('native_ui.time.monotonic',return_value=100):self.app.send('Create a list')
        with patch('native_ui.time.monotonic',return_value=100.2):self.app.poll()
        self.assertEqual(self.app.device.agent,'thinking')
        self.assertIsNotNone(self.app.pending)
        with patch('native_ui.time.monotonic',return_value=110.1):self.app.poll()
        self.assertIsNone(self.app.pending)

    def test_logo_returns_every_arrow_to_default_length_without_a_jump(self):
        screen=self.app.screen
        screen.arrow_waiting=True
        screen.arrows=[dict(start=0,duration=1000,old=0,target=value) for value in (8,-6,12,-10,4)]
        screen.time=500
        before=list(screen.logo_offsets(True))
        self.assertTrue(all(value!=0 for value in before))
        self.assertEqual(screen.logo_offsets(False),before)
        screen.time=640
        middle=screen.logo_offsets(False)
        for old,value in zip(before,middle):self.assertAlmostEqual(value,old/2)
        screen.time=780
        self.assertEqual(screen.logo_offsets(False),[0.]*5)
        self.assertIsNone(screen.arrow_settle)
        screen.time=1500
        self.assertEqual(screen.logo_offsets(False),[0.]*5)

    def test_logo_resumes_from_settling_position_and_reduced_motion_resets(self):
        screen=self.app.screen
        screen.arrow_waiting=True;screen.arrow_values=[8,-6,12,-10,4];screen.time=500
        screen.logo_offsets(False);screen.time=600
        settling=list(screen.logo_offsets(False))
        self.assertEqual(screen.logo_offsets(True),settling)
        screen.prefs['motion']=False
        self.assertEqual(screen.logo_offsets(True),[0.]*5)
        self.assertIsNone(screen.arrow_settle)

    def test_transcription_to_backend_wait_keeps_arrow_motion_continuous(self):
        self.app.screen.arrow_waiting=True
        self.app.screen.arrows=[dict(start=0,duration=1000,old=0,target=8) for _ in range(5)]
        self.app.screen.time=500
        before=self.app.screen.logo_offsets(True)
        self.app.send('Hello')
        self.assertEqual(self.app.screen.logo_offsets(True),before)

    def fixture(self,name):
        return json.loads((Path(__file__).resolve().parents[1]/'contract/fixtures/v2'/name).read_text())

    def deliver(self,turn):
        self.app.backend='gemini';self.app.live=True
        with patch('threading.Thread'):self.app.send('test request')
        self.app.events.put((self.app.pending['number'],turn));self.app.poll();self.paint()
        self.finish_response()
        self.paint(500)

    def finish_response(self):
        # Advance rendered frames, including word fades and the reading pause.
        self.paint()
        for _ in range(80):
            self.paint(100);self.app.poll()
            if self.app.after_response is None:break
        self.assertIsNone(self.app.after_response)

    def settle_navigation(self):
        for _ in range(60):
            self.paint(100);self.app.poll()
        self.paint(400)

    def test_navigation_to_settings_agent_wheel_and_existing_app_without_generation(self):
        count=len(self.app.device.registry)
        self.deliver(navigation('settings'));self.settle_navigation()
        self.assertEqual(self.app.device.current()['id'],'settings')
        self.assertEqual(len(self.app.device.registry),count)
        self.deliver(navigation('agent'))
        self.assertIsNone(self.app.device.current());self.assertFalse(self.app.screen.launcher)
        self.deliver(navigation('apps'))
        self.assertTrue(self.app.screen.launcher)
        generated=self.fixture('shopping.json');self.app.select_app(generated)
        self.deliver(navigation('app',generated['id']));self.settle_navigation()
        self.assertEqual(self.app.device.current()['id'],generated['id'])
        self.assertEqual(self.app.device.last_turn['intent'],'navigate')
        saved=json.loads(self.store.read_text());self.assertEqual(saved['last_turn']['destination'],'app')

    def test_message_keeps_apps_unchanged_and_persists_intent(self):
        before=list(self.app.device.registry)
        self.deliver(message('Hello! How can I help?'))
        self.assertEqual(self.app.device.registry,before)
        self.paint(500)
        self.assertEqual(self.app.screen.transcript.text,'Hello! How can I help?')
        self.assertEqual(json.loads(self.store.read_text())['last_turn']['intent'],'message')

    def test_invalid_response_never_changes_or_saves_generated_apps(self):
        self.deliver({'schema_version':2,'intent':'message','op':'propose','say':'Made it','app':self.fixture('shopping.json')})
        self.assertEqual(len(self.app.device.registry),5)
        self.assertIsNone(self.app.device.last_turn)
        self.assertIn('could not be used',self.app.device.say)

    def test_component_input_button_and_list_share_state_and_survive_restart(self):
        self.app.select_app(self.fixture('shopping.json'));self.open('shopping')
        self.assertTrue(any(hit.act=='component_input' for hit in self.app.screen.hits))
        self.activate('component_input',text='entry');self.app.on_text('Coffee')
        self.activate('key',text='done');self.activate('component_action',text='append_item')
        app=self.app.device.current();state=fields(app)
        self.assertEqual(state['items']['value'][-1]['label'],'Coffee')
        self.assertEqual(state['entry']['value'],'')
        self.activate('component_item',text='items',index=0)
        self.assertTrue(fields(app)['items']['value'][0]['checked'])
        self.activate('component_action',text='remove_done')
        self.assertEqual([item['label'] for item in fields(app)['items']['value']],['Bread','Coffee'])
        restored=NativeApp('http://unused','none',False,self.store);self.addCleanup(restored.close)
        self.assertEqual(fields(restored.device.find('shopping'))['items']['value'],fields(app)['items']['value'])

    def test_component_number_progress_toggle_and_bound_text_render(self):
        app=self.fixture('shopping.json')
        app['state']['fields'] += [{'id':'count','type':'number','value':3,'min':0,'max':10},
                                  {'id':'enabled','type':'boolean','value':False}]
        app['components']=[{'id':'text_view','type':'text','text':'','bind':'entry'},
                           {'id':'count_view','type':'number','label':'Count','bind':'count','unit':'times'},
                           {'id':'count_progress','type':'progress','label':'Goal','bind':'count','goal':10,'unit':'times'},
                           {'id':'enabled_toggle','type':'toggle','label':'Enabled','bind':'enabled'}]+app['components']
        app['actions'].append({'id':'increase','action':'increment','target':'count','amount':2})
        validate_app(app);self.app.select_app(app);self.open('shopping')
        self.assertGreater(self.app.screen.content_h,500)
        self.activate('component_toggle',text='enabled')
        self.activate('component_action',text='increase')
        self.assertTrue(fields(app)['enabled']['value']);self.assertEqual(fields(app)['count']['value'],5)

    def test_validated_mutation_updates_app_and_persists_turn(self):
        self.app.select_app(self.fixture('shopping.json'))
        self.deliver(self.fixture('update-shopping.json')['turn'])
        self.assertEqual(fields(self.app.device.find('shopping'))['items']['value'][-1]['label'],'Coffee')
        self.assertEqual(json.loads(self.store.read_text())['last_turn']['intent'],'update_app')

    def test_demo_navigation_does_not_wait_for_app_generation_preview(self):
        with patch('native_ui.time.monotonic',return_value=100):self.app.send('Take me to settings')
        with patch('native_ui.time.monotonic',return_value=100.1):self.app.poll()
        self.assertIsNone(self.app.device.current())
        self.assertIsNotNone(self.app.after_response)
        self.settle_navigation()
        self.assertEqual(self.app.device.current()['id'],'settings')
        self.assertEqual(len(self.app.device.registry),5)

    def test_live_generated_counter_fixture_buttons_increment_and_reset(self):
        app=self.fixture('counter.json');self.app.select_app(app);self.open(app['id'])
        self.activate('component_action',text='act_increment')
        self.assertEqual(fields(app)['count']['value'],1)
        self.activate('component_action',text='act_reset')
        self.assertEqual(fields(app)['count']['value'],0)

    def test_legacy_generated_apps_migrate_with_original_registry_backup(self):
        legacy={'id':'old_list','module':'checklist','title':'Old list','state':{'cursor':0,'items':[{'label':'Keep this','checked':True}]}}
        self.app.device.registry.append(legacy);self.app.device.save(self.store)
        restored=NativeApp('http://unused','none',False,self.store);self.addCleanup(restored.close)
        app=restored.device.find('old_list')
        self.assertEqual(app['module'],'composed')
        self.assertEqual(fields(app)['items']['value'][0]['label'],'Keep this')
        self.assertTrue(fields(app)['items']['value'][0]['checked'])
        saved=json.loads(self.store.with_name('registry.pre-components.json').read_text())
        self.assertEqual(saved['registry'][-1]['module'],'checklist')

    def test_pi_orientation_uses_same_touch_targets(self):
        for turn in ('right','left','none'):
            size=(800,480) if turn!='none' else (480,800)
            window_point=screen_point(*VOICE.center,size,turn)
            point=phone_point(*window_point,size,turn)
            self.assertTrue(VOICE.collidepoint(point))


if __name__=='__main__':unittest.main()
