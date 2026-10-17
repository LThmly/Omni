"""Exercise the same pygame flow used by desktop simulator and Pi kiosk."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from native_ui import NativeApp, calculate, default_apps, VOICE
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

    def test_pi_orientation_uses_same_touch_targets(self):
        for turn in ('right','left','none'):
            size=(800,480) if turn!='none' else (480,800)
            window_point=screen_point(*VOICE.center,size,turn)
            point=phone_point(*window_point,size,turn)
            self.assertTrue(VOICE.collidepoint(point))


if __name__=='__main__':unittest.main()
