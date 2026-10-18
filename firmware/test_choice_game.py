"""Playable generated games: complete rules, atomic scoring, touch and reveal."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import pygame
import test_native_ui as harness
from contract.runtime import ContractError,apply_operations,fields,validate_app
from game_art import gesture


def rps():
    return json.loads((Path(__file__).resolve().parents[1]/'contract/fixtures/v2/rock-paper-scissors.json').read_text())


def play(app,choice):
    component=app['components'][0]
    return dict(action='play_choice',target=component['bind'],choice=choice,
                **{k:component[k] for k in ('player','opponent','wins','losses','draws','choices')})


class RulesTest(unittest.TestCase):
    def test_same_component_supports_custom_rules_and_offline_rps_generation(self):
        from native_ui import demo_app
        generated=demo_app('Create a rock paper scissors game',[])
        self.assertTrue(any(c['type']=='choice_game' for c in generated['components']))
        app=rps();choices=app['components'][0]['choices']
        names={'rock':'water','paper':'leaf','scissors':'flame'}
        for choice in choices:
            choice['id']=names[choice['id']];choice['label']=choice['id'].title();choice['icon']=choice['id']
            choice['beats']=[names[b] for b in choice['beats']]
        validate_app(app)
        with patch('contract.runtime.random.choice',return_value='flame'):
            result=fields(apply_operations(app,[play(app,'water')]))
        self.assertEqual(result['result']['value'],'win')
        self.assertEqual(result['wins']['value'],1)

    def test_all_nine_matchups_choose_independently_and_update_exactly_one_score(self):
        app=rps();original=copy.deepcopy(app)
        beats={'rock':'scissors','paper':'rock','scissors':'paper'}
        for player in beats:
            for opponent in beats:
                with self.subTest(player=player,opponent=opponent),patch('contract.runtime.random.choice',return_value=opponent) as random:
                    updated=apply_operations(app,[play(app,player)]);state=fields(updated)
                    random.assert_called_once_with(list(beats))
                    outcome='draw' if player==opponent else 'win' if beats[player]==opponent else 'loss'
                    self.assertEqual(state['result']['value'],outcome)
                    self.assertEqual(state['player']['value'],player)
                    self.assertEqual(state['opponent']['value'],opponent)
                    for key,result in (('wins','win'),('losses','loss'),('draws','draw')):
                        self.assertEqual(state[key]['value'],int(result==outcome))
        self.assertEqual(app,original)

    def test_bad_graph_bindings_and_unknown_art_are_rejected(self):
        for kind in ('self','unknown','duplicate','both_win','no_winner','shared_state','wrong_type','bad_icon','bad_score'):
            app=rps();c=app['components'][0]
            if kind=='self':c['choices'][0]['beats']=['rock']
            elif kind=='unknown':c['choices'][0]['beats']=['missing']
            elif kind=='duplicate':c['choices'][0]['beats']=['scissors','scissors']
            elif kind=='both_win':c['choices'][0]['beats'].append('paper')
            elif kind=='no_winner':c['choices'][1]['beats']=['scissors']
            elif kind=='shared_state':c['opponent']=c['player']
            elif kind=='wrong_type':c['wins']='result'
            elif kind=='bad_icon':c['choices'][0]['icon']='https://untrusted/image.png'
            else:fields(app)['wins']['value']=.5
            with self.subTest(kind=kind),self.assertRaises(ContractError):validate_app(app)

    def test_game_round_is_atomic_and_score_limit_does_not_silently_drop_rounds(self):
        app=rps();original=copy.deepcopy(app)
        with patch('contract.runtime.random.choice',return_value='scissors'):
            with self.assertRaises(ContractError):apply_operations(app,[play(app,'rock'),dict(action='calculate',target='wins',operator='divide',left={'literal':1},right={'literal':0})])
            self.assertEqual(app,original)
            fields(app)['wins']['value']=fields(app)['wins']['max']
            with self.assertRaises(ContractError):apply_operations(app,[play(app,'rock')])
            self.assertEqual(fields(app)['result']['value'],'')
        with self.assertRaises(ContractError):apply_operations(app,[play(app,'invalid')])


class GameUITest(unittest.TestCase):
    setUp=harness.NativeUITest.setUp
    paint=harness.NativeUITest.paint
    activate=harness.NativeUITest.activate
    open=harness.NativeUITest.open
    touch=harness.NativeUITest.touch

    @classmethod
    def setUpClass(cls):pygame.init()

    def install(self):
        app=rps();self.app.select_app(app);self.open(app['id']);return app

    def test_touch_round_reveal_blocks_double_scoring_and_persists_result(self):
        app=self.install()
        self.assertEqual(self.app.screen.scroll_limit,0)
        moves=[h for h in self.app.screen.hits if h.act=='component_game']
        self.assertEqual(len(moves),3)
        self.assertTrue(all(h.rect.height>=100 for h in moves))
        with patch('contract.runtime.random.choice',return_value='scissors'):
            self.touch(moves[0],dx=7,dy=5)
            self.assertEqual(fields(app)['wins']['value'],1)
            self.app.activate(moves[0])
        self.assertEqual(fields(app)['wins']['value'],1)
        self.assertFalse(any(h.act=='component_game' for h in self.app.screen.hits))
        self.paint(700)
        self.assertEqual(len([h for h in self.app.screen.hits if h.act=='component_game']),3)
        saved=json.loads(self.store.read_text())
        stored=next(a for a in saved['registry'] if a['id']==app['id'])
        self.assertEqual(fields(stored)['result']['value'],'win')

    def test_reduced_motion_scores_immediately_and_new_match_resets_all_state(self):
        self.app.prefs['motion']=False;app=self.install()
        move=next(h for h in self.app.screen.hits if h.act=='component_game' and h.index==1)
        with patch('contract.runtime.random.choice',return_value='rock'):self.app.activate(move)
        self.paint()
        self.assertEqual(fields(app)['wins']['value'],1)
        self.assertEqual(len([h for h in self.app.screen.hits if h.act=='component_game']),3)
        self.activate('component_confirm',text='reset_match')
        self.activate('component_confirm',text='reset_match')
        self.assertTrue(all(f['value']==('' if f['type']=='text' else 0) for f in fields(app).values()))

    def test_assets_are_cached_distinct_and_render_in_both_themes(self):
        self.install()
        for theme,ink,paper in (('dark',(255,255,255),(0,0,0)),('light',(0,0,0),(255,255,255))):
            self.app.prefs['theme']=theme;self.paint()
            art=[gesture(icon,96,ink,paper) for icon in ('rock','paper','scissors','flame','water','leaf')]
            self.assertIs(art[0],gesture('rock',96,ink,paper))
            self.assertEqual(len({pygame.image.tobytes(a,'RGBA') for a in art}),6)


if __name__=='__main__':unittest.main()
