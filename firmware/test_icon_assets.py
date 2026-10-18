"""Offline catalog coverage, contracts, theme rendering and logo-picker workflows."""
import copy
import json
from pathlib import Path
import unittest
import pygame
import test_native_ui as harness
from contract.asset_catalog import catalog,search,resolve,for_prompt,app_icon,component_icon
from contract.runtime import ContractError,validate_app,apply_operations,fields
from icon_assets import image,mask,_image,archive


def example():
    return json.loads((Path(__file__).resolve().parents[1]/'contract/fixtures/v2/shopping.json').read_text())


class CatalogTest(unittest.TestCase):
    def test_whole_pack_is_present_decodable_and_caches_stay_bounded(self):
        self.assertGreaterEqual(catalog()['count'],1000)
        for name in catalog()['icons']:
            with self.subTest(icon=name):
                art=image(name,32,(255,255,255),(0,0,0))
                self.assertEqual(art.get_size(),(32,32))
                self.assertGreater(art.get_bounding_rect().width,0)
        self.assertLessEqual(mask.cache_info().currsize,96)
        self.assertLessEqual(_image.cache_info().currsize,192)
        self.assertIn('ISC License',(Path(__file__).resolve().parents[1]/'assets/icons/LICENSE-LUCIDE.txt').read_text())

    def test_retrieval_exposes_specific_assets_and_short_prompt_context(self):
        for word,expected in (('ball','basketball'),('person','person-standing'),('soccer','soccer-ball'),('rock','rps-rock')):
            self.assertEqual(resolve(word),expected)
            self.assertEqual(search(word,1),[expected])
        context=for_prompt('Create a basketball practice tracker')
        self.assertIn('basketball',{a['id'] for a in context['icons']})
        self.assertLessEqual(len(context['icons']),64)
        for a in context['icons']:self.assertIsNotNone(resolve(a['id']))
        for kind in ('number','number_input','timer','pacer','input','toggle','progress','list','key_value_log','inventory_list','deck_card','stat_grid','bar_chart','button','confirm_button'):
            self.assertIsNotNone(resolve(component_icon(kind,'Reset match')))
        self.assertNotEqual(app_icon({'title':'Fitness'}),app_icon({'title':'Budget'}))

    def test_asset_references_are_validated_at_every_contract_entry_point(self):
        app=example();app['icon']='basketball';app['components'][0]['icon']='list-checks'
        fields(app)['items']['value'][0]['icon']='apple'
        app['components'].insert(0,dict(id='art',type='illustration',icon='person',label='Your daily list',size='medium'))
        validate_app(app)
        for location in ('app','component','item','illustration'):
            bad=copy.deepcopy(app)
            if location=='app':bad['icon']='not-an-offline-asset'
            elif location=='component':bad['components'][1]['icon']='../../private'
            elif location=='illustration':bad['components'][0]['icon']='https://example.com/image.png'
            else:fields(bad)['items']['value'][0]['icon']='made-up-asset'
            with self.subTest(location=location),self.assertRaises(ContractError):validate_app(bad)
        original=copy.deepcopy(app)
        items=copy.deepcopy(fields(app)['items']['value']);items[0]['icon']='invented'
        with self.assertRaises(ContractError):apply_operations(app,[dict(action='set',target='items',value=items)])
        self.assertEqual(app,original)

    def test_theme_recolor_and_aliases_preserve_alpha_and_cached_surfaces(self):
        for name in ('basketball','person-standing','rps-paper','book-open'):
            light=image(name,96,(0,0,0),(255,255,255));dark=image(name,96,(255,255,255),(0,0,0))
            self.assertEqual(pygame.mask.from_surface(light).count(),pygame.mask.from_surface(dark).count())
            self.assertNotEqual(pygame.image.tobytes(light,'RGBA'),pygame.image.tobytes(dark,'RGBA'))
            self.assertIs(light,image(name,96,(0,0,0),(255,255,255)))
        self.assertIs(image('person',48,(0,0,0)),image('person-standing',48,(0,0,0)))


class PickerTest(unittest.TestCase):
    setUp=harness.NativeUITest.setUp
    paint=harness.NativeUITest.paint
    activate=harness.NativeUITest.activate
    open=harness.NativeUITest.open
    touch=harness.NativeUITest.touch
    key=harness.NativeUITest.key

    @classmethod
    def setUpClass(cls):pygame.init()

    def install(self):
        app=example();self.app.select_app(app);self.open(app['id']);return app

    def test_picker_search_touch_selection_and_persistence_leave_content_intact(self):
        app=self.install();state=copy.deepcopy(app['state'])
        self.touch(next(h for h in self.app.screen.hits if h.act=='app_icon_picker'))
        self.assertIsNotNone(self.app.screen.asset_picker)
        self.assertFalse(any(h.act.startswith('component_') for h in self.app.screen.hits))
        self.app.on_text('basketball');self.paint()
        choice=next(h for h in self.app.screen.hits if h.act=='asset_select' and h.text=='basketball')
        self.touch(choice,dx=5,dy=4)
        self.assertEqual(app['icon'],'basketball');self.assertEqual(app['state'],state)
        saved=json.loads(self.store.read_text())
        self.assertEqual(next(a for a in saved['registry'] if a['id']==app['id'])['icon'],'basketball')
        self.assertIsNone(self.app.screen.asset_picker)

    def test_picker_pages_empty_search_keyboard_cancel_and_auto(self):
        app=self.install();app['icon']='basketball'
        for theme in ('dark','light'):
            self.app.prefs['theme']=theme;self.activate('app_icon_picker')
            before=[h.text for h in self.app.screen.hits if h.act=='asset_select']
            self.activate('asset_page',amount=1)
            self.assertNotEqual(before,[h.text for h in self.app.screen.hits if h.act=='asset_select'])
            self.activate('asset_search')
            self.assertFalse(any(h.act=='asset_select' and h.rect.bottom>365 for h in self.app.screen.hits))
            self.app.keyboard_key('zzzzqxxxyyy');self.app.keyboard_key('done');self.paint()
            self.assertFalse(any(h.act=='asset_select' for h in self.app.screen.hits))
            self.key(pygame.K_ESCAPE);self.paint()
            self.assertIsNone(self.app.screen.asset_picker)
        self.activate('app_icon_picker');self.activate('asset_auto')
        self.assertNotIn('icon',app)
        self.assertEqual(self.app.device.current()['id'],app['id'])

    def test_illustrations_and_item_art_keep_controls_reachable(self):
        app=self.install()
        app['components'].insert(0,dict(id='hero_art',type='illustration',icon='basketball',label='Basketball practice',size='large'))
        fields(app)['items']['value'][0]['icon']='person-running'
        fields(app)['entry']['value']='Practice'
        for theme in ('dark','light'):
            self.app.prefs['theme']=theme;self.paint()
            self.assertTrue(any(h.act=='back' for h in self.app.screen.hits))
            self.assertTrue(any(h.act=='component_action' for h in self.app.screen.hits))
        app['components']=[dict(id='cards',type='deck_card',bind='items',label='Practice cards',icon='layers')]
        self.app.screen.scroll=0;self.paint()
        self.assertEqual(len([h for h in self.app.screen.hits if h.act=='component_deck_nav']),2)


if __name__=='__main__':unittest.main()
