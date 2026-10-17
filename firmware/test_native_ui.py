"""Exercise the same pygame flow used by desktop simulator and Pi kiosk."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import pygame
from native_ui import NativeApp, PartialSpeechDemo, calculate, default_apps, VOICE
from phone import Hit, phone_point, screen_point


class NativeUITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store=Path(self.temp.name)/'registry.json'
        self.app=NativeApp('http://unused','none',False,self.store)
        self.ticks=1000
        self.paint()

    def paint(self,delta=0):
        self.ticks+=delta
        self.app.screen.paint(self.app.phone,self.app.device,self.ticks,self.app.draft)

    def activate(self,action,**kwargs):
        self.app.activate(Hit((0,0,1,1),action,**kwargs));self.paint(600)

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

    def test_arithmetic_rejects_code_and_supports_negation(self):
        self.assertEqual(calculate('-(2+3)*4'),'-20')
        with self.assertRaises(ValueError):calculate('__import__("os")')
        with self.assertRaises(ValueError):calculate('2**1000000')

    def test_live_reply_selection_and_cancelled_request(self):
        self.app.live=True
        with patch.object(self.app, 'fetch_native'):
            self.app.send('make something')
        pending=self.app.pending
        proposal={'op':'propose','app':{'id':'new_list','title':'New list','module':'checklist',
                  'state':{'cursor':0,'items':[{'label':'Item','checked':False}]}}}
        self.app.events.put((pending['number'],proposal))
        with patch('native_ui.time.monotonic',return_value=pending['due']+1):self.app.poll()
        self.assertEqual(self.app.device.registry[self.app.screen.selection]['id'],'new_list')
        self.assertTrue(self.app.screen.launcher)
        self.app.live=False
        self.app.send('water')
        self.key(pygame.K_ESCAPE)
        self.app.poll()
        self.assertIsNone(self.app.pending)
        self.assertEqual(len(self.app.device.registry),6)
        self.assertEqual(self.app.device.agent,'idle')

    def test_live_input_updates_while_held_and_shows_submitted_request(self):
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

    def test_hidden_input_persists_and_does_not_change_the_request(self):
        self.open('settings')
        self.activate('setting',index=4)
        self.assertFalse(self.app.prefs['show_input'])
        restored=NativeApp('http://unused','none',False,self.store)
        self.assertFalse(restored.prefs['show_input'])
        self.app.screen.transition=None
        self.app.screen.last_view='home'
        self.app.set_launcher(False)
        self.app.draft='Create a packing list'
        with patch('pygame.time.get_ticks',side_effect=[1000,1500]):
            self.paint()
            self.app.on_down(VOICE.center)
            with patch.object(self.app.screen,'label',wraps=self.app.screen.label) as label:
                self.paint()
                texts=[call.args[1] for call in label.call_args_list]
                self.assertNotIn('Listening',texts)
                self.assertNotIn('Create a packing list',texts)
            self.app.on_up(VOICE.center)
        self.assertEqual(self.app.pending['request'],'Create a packing list')

    def test_live_input_keeps_latest_lines_and_settings_back_is_accessible(self):
        self.app.draft='A'*200+' latest words'
        self.paint();self.paint(400)
        frames=list(self.app.screen.transcript.frames(self.ticks))
        visible=[word for word,x,y,alpha in frames if 0<=y<66 and alpha>0]
        self.assertEqual(visible[-2:],['latest','words'])
        self.assertGreater(self.app.screen.transcript.scroll(self.ticks),0)
        self.open('settings')
        settings=[hit for hit in self.app.screen.hits if hit.act=='setting']
        self.assertEqual(len(settings),6)
        self.assertTrue(all(hit.rect.bottom<800 for hit in settings))
        self.app.screen.setting_cursor=5
        self.app.scroll_input(1)
        self.assertEqual(self.app.screen.setting_cursor,0)
        self.activate('setting',index=5)
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

    def test_partial_demo_custom_phrase_and_hidden_visual(self):
        self.app.prefs['show_input']=False
        self.app.prefs['motion']=False
        self.app.draft='Track my daily water'
        with patch('pygame.time.get_ticks',return_value=1000):self.app.on_down(VOICE.center)
        self.app.update_speech_preview(10000)
        self.assertEqual(self.app.screen.listening_text,'track my daily water')
        with patch.object(self.app.screen,'label',wraps=self.app.screen.label) as label:
            self.paint()
            self.assertNotIn('track my daily water',[call.args[1] for call in label.call_args_list])
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

    def test_final_transcript_remains_visible_when_agent_returns_idle(self):
        self.app.screen.submitted_text='Create a note taking app'
        self.app.device.agent='idle'
        self.app.draft=''
        self.paint()
        self.assertEqual(self.app.screen.transcript.text,'Create a note taking app')
        self.app.on_down(VOICE.center)
        self.assertEqual(self.app.screen.submitted_text,'')
        self.paint()
        self.assertEqual(self.app.screen.transcript.text,'')

    def test_direct_gemini_reply_creates_and_selects_app_through_shared_flow(self):
        self.app.backend='gemini';self.app.live=True
        proposal={'op':'propose','app':{'id':'voice_list','title':'Voice list','module':'checklist',
                  'state':{'cursor':0,'items':[{'label':'Milk','checked':False}]}}}
        with patch('threading.Thread') as worker:
            self.app.send('Create a shopping list')
        payload,number=worker.call_args.kwargs['args']
        self.assertEqual(payload['registry'],[])
        with patch('cloud.try_turn.ask',return_value=proposal) as ask:
            self.app.fetch_native(payload,number)
        ask.assert_called_once_with('Create a shopping list',[],wav_base64=None)
        with patch('native_ui.time.monotonic',return_value=self.app.pending['due']+1):self.app.poll()
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

    def test_pi_orientation_uses_same_touch_targets(self):
        for turn in ('right','left','none'):
            size=(800,480) if turn!='none' else (480,800)
            window_point=screen_point(*VOICE.center,size,turn)
            point=phone_point(*window_point,size,turn)
            self.assertTrue(VOICE.collidepoint(point))


if __name__=='__main__':unittest.main()
