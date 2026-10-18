"""Complete generated-app workflows, layout, and the expanded strict contract."""
import copy
import json
from pathlib import Path
import unittest
import pygame
import test_native_ui as native_tests
from phone import Hit
from contract.runtime import ContractError,apply_operations,fields,validate_app
from contract.build_schema import (TEXT_COMPONENTS,NUMBER_COMPONENTS,GOAL_COMPONENTS,
                                  ITEM_COMPONENTS,TOGGLE_COMPONENTS,INPUT_COMPONENTS,BUTTON_COMPONENTS)


def expense():return json.loads((Path(__file__).resolve().parents[1]/'contract/fixtures/v2/expense-log.json').read_text())


class GeneratedAppsTest(unittest.TestCase):
    # Share only the established temporary-profile/input harness, not its tests.
    setUp=native_tests.NativeUITest.setUp
    paint=native_tests.NativeUITest.paint
    activate=native_tests.NativeUITest.activate
    open=native_tests.NativeUITest.open
    fixture=native_tests.NativeUITest.fixture

    @classmethod
    def setUpClass(cls):pygame.init()

    def install_expense(self):
        app=expense();validate_app(app);self.app.select_app(app);self.open(app['id']);return app

    def test_pages_reference_real_components_and_remain_backward_compatible(self):
        app=expense();validate_app(app)
        for change in ('missing','duplicate','hidden','duplicate_page'):
            bad=copy.deepcopy(app)
            if change=='missing':bad['pages'][0]['components'].append('missing')
            elif change=='duplicate':bad['pages'][0]['components']*=2
            elif change=='hidden':bad['pages'][1]['components'].remove('save_button')
            else:bad['pages'][1]['id']=bad['pages'][0]['id']
            with self.subTest(change=change),self.assertRaises(ContractError):validate_app(bad)
        del app['pages'];validate_app(app)

    def test_expense_save_is_atomic_and_calculates_totals(self):
        app=expense();state=fields(app);state['entry']['value']='Groceries';state['amount']['value']=24.5
        original=copy.deepcopy(app)
        updated=apply_operations(app,[{k:v for k,v in app['actions'][0].items() if k!='id'}])
        self.assertEqual(app,original)
        result=fields(updated)
        self.assertEqual(result['total']['value'],24.5)
        self.assertEqual(result['remaining']['value'],975.5)
        self.assertEqual(result['history']['value'][0]['label'],'Groceries: 24.5')
        self.assertEqual(result['amount']['value'],0)
        self.assertEqual(result['entry']['value'],'')
        steps=copy.deepcopy(app['actions'][0]['steps']);steps.append(dict(action='calculate',target='total',operator='divide',left={'literal':1},right={'literal':0}))
        with self.assertRaises(ContractError):apply_operations(app,[dict(action='batch',steps=steps)])
        self.assertEqual(app,original)

    def test_calculations_reject_wrong_types_bounds_and_nested_batches(self):
        app=expense()
        base=dict(action='calculate',target='total',operator='multiply',left={'field':'amount'},right={'literal':2})
        for change in ('wrong_field','overflow','expression','nested'):
            op=copy.deepcopy(base)
            if change=='wrong_field':op['left']={'field':'entry'}
            elif change=='overflow':op['left']={'literal':1e30}
            elif change=='expression':op['left']={'expression':'__import__("os")'}
            else:op=dict(action='batch',steps=[dict(action='batch',steps=[base])])
            with self.subTest(change=change),self.assertRaises(ContractError):apply_operations(app,[op])

    def test_page_navigation_numeric_form_and_pinned_save_workflow(self):
        app=self.install_expense()
        self.activate('app_page',text='add')
        self.assertTrue(any(h.act=='component_number_input' for h in self.app.screen.hits))
        self.assertFalse(any(h.act=='component_action' for h in self.app.screen.hits))
        self.activate('component_number_input',text='amount')
        self.app.screen.keyboard['text']='32.75';self.app.keyboard_key('done');self.paint()
        self.activate('component_input',text='entry')
        self.app.keyboard_key('Train ticket');self.app.keyboard_key('done');self.paint()
        button=next(h for h in self.app.screen.hits if h.act=='component_action')
        self.assertGreaterEqual(button.rect.y,self.app.screen.app_body.bottom)
        self.activate('component_action',text='save_expense')
        self.assertEqual(fields(app)['total']['value'],32.75)
        self.activate('app_page',text='history')
        self.assertTrue(any(h.act=='component_item_edit' for h in self.app.screen.hits))
        saved=json.loads(self.store.read_text())
        self.assertEqual(fields(next(a for a in saved['registry'] if a['id']==app['id']))['total']['value'],32.75)

    def test_invalid_numeric_edit_does_not_corrupt_state(self):
        app=self.install_expense();self.activate('app_page',text='add')
        self.activate('component_number_input',text='amount')
        for value in ('NaN','-5','not a number','2000001'):
            self.app.screen.keyboard['text']=value;self.app.keyboard_key('done')
            self.assertIsNotNone(self.app.screen.keyboard)
            self.assertEqual(fields(app)['amount']['value'],0)
        self.app.screen.keyboard['text']='12.5';self.app.keyboard_key('done')
        self.assertEqual(fields(app)['amount']['value'],12.5)

    def test_long_list_can_scroll_to_last_row_without_losing_navigation(self):
        app=self.install_expense()
        fields(app)['history']['value']=[dict(id='i_'+str(i),label='Long saved entry '+str(i)+' with enough detail to wrap onto more than one line',checked=False) for i in range(50)]
        self.activate('app_page',text='history')
        for _ in range(120):self.app.scroll_input(1)
        self.paint()
        self.assertEqual(self.app.screen.scroll,self.app.screen.scroll_limit)
        self.assertTrue(any(h.act=='component_item_edit' and h.index==49 for h in self.app.screen.hits))
        self.assertTrue(any(h.act=='back' for h in self.app.screen.hits))
        self.activate('app_page',text='overview')
        self.assertEqual(self.app.screen.scroll,0)
        self.activate('app_page',text='history')
        self.assertEqual(self.app.screen.scroll,self.app.screen.scroll_limit)

    def test_collection_entries_can_be_renamed_and_removed(self):
        app=self.install_expense();fields(app)['history']['value']=[dict(id='one',label='Old name: 12',checked=False)]
        self.activate('app_page',text='history')
        self.activate('component_item_edit',text='history',index=0)
        self.app.screen.keyboard['text']='New name: 18';self.app.keyboard_key('done');self.paint()
        self.assertEqual(fields(app)['history']['value'][0]['label'],'New name: 18')
        self.activate('component_item_remove',text='history',index=0)
        self.assertEqual(fields(app)['history']['value'],[])
        self.assertEqual(fields(app)['total']['value'],0)
        self.app.activate(Hit((0,0,1,1),'undo_item'));self.paint()
        self.assertEqual(fields(app)['history']['value'][0]['label'],'New name: 18')
        self.assertEqual(fields(app)['total']['value'],18)

    def test_on_change_recalculates_edits_and_rolls_back_invalid_records(self):
        app=expense();before=copy.deepcopy(app)
        op=dict(action='set',target='history',value=[dict(id='one',label='Lunch: 15.5',checked=False)])
        updated=apply_operations(app,[op]);self.assertEqual(fields(updated)['total']['value'],15.5)
        self.assertEqual(fields(updated)['remaining']['value'],984.5)
        op['value'][0]['label']='Not a numeric record'
        with self.assertRaises(ContractError):apply_operations(app,[op])
        self.assertEqual(app,before)
        bad=copy.deepcopy(app);bad['components'][0]['on_change']='missing'
        with self.assertRaises(ContractError):validate_app(bad)

    def test_empty_save_never_clears_a_numeric_entry(self):
        app=expense();fields(app)['amount']['value']=45
        before=copy.deepcopy(app)
        with self.assertRaises(ContractError):apply_operations(app,[{k:v for k,v in app['actions'][0].items() if k!='id'}])
        self.assertEqual(app,before)

    def test_numeric_touch_keypad_includes_decimal_and_commits_on_done(self):
        app=self.install_expense();self.activate('app_page',text='add')
        self.activate('component_number_input',text='amount')
        keys={h.text:h for h in self.app.screen.hits if h.act=='key'}
        self.assertTrue({'clear','backspace','done','-','.'}<=set(keys))
        self.assertTrue(all(h.rect.width>=44 and h.rect.height>=44 for h in keys.values()))
        for key in ('clear','2','1','.','5'):
            self.activate('key',text=key)
        self.assertEqual(fields(app)['amount']['value'],0)
        self.activate('key',text='done')
        self.assertEqual(fields(app)['amount']['value'],21.5)

    def test_slider_drag_previews_and_commits_bounded_value(self):
        app=self.install_expense()
        app.pop('pages');app['components']=[dict(id='slider',type='xy_pad',label='Level',bind='amount',goal=100,unit='')]
        self.paint()
        hit=next(h for h in self.app.screen.hits if h.act=='component_xy')
        self.app.on_down(hit.rect.center)
        end=(hit.rect.right-20,hit.rect.centery)
        self.app.on_move(end);self.paint()
        self.assertEqual(fields(app)['amount']['value'],0)
        self.app.on_up(end);self.paint()
        self.assertEqual(fields(app)['amount']['value'],100)

    def test_undo_notice_never_blocks_pinned_actions_and_expires(self):
        app=self.fixture('shopping.json');self.app.select_app(app);self.open(app['id'])
        self.activate('component_item_remove',text='items',index=0)
        notice=next(h for h in self.app.screen.hits if h.act=='undo_item')
        self.assertLessEqual(notice.rect.bottom,self.app.screen.app_body.bottom)
        self.paint(4100)
        self.assertIsNone(self.app.screen.removed_item)
        self.assertFalse(any(h.act=='undo_item' for h in self.app.screen.hits))

    def test_timer_updates_persistent_state_and_stops_at_zero(self):
        app=self.install_expense()
        self.app.screen.component_timers[app['id']+':amount']=dict(running=True,started=self.ticks,base=3,initial=3)
        self.paint(2000);self.app.poll()
        self.assertEqual(fields(app)['amount']['value'],1)
        self.paint(2000);self.app.poll()
        self.assertEqual(fields(app)['amount']['value'],0)
        self.assertFalse(self.app.screen.component_timers[app['id']+':amount']['running'])

    def test_every_registered_component_renders_in_both_themes(self):
        groups=((TEXT_COMPONENTS,'text'),(NUMBER_COMPONENTS+GOAL_COMPONENTS,'number'),
                (ITEM_COMPONENTS,'items'),(TOGGLE_COMPONENTS,'boolean'),(INPUT_COMPONENTS,'text'),(BUTTON_COMPONENTS,None))
        app=self.install_expense()
        for theme in ('light','dark'):
            self.app.prefs['theme']=theme
            for kinds,field_type in groups:
                for kind in kinds:
                    component=dict(id='view',type=kind)
                    if kind in TEXT_COMPONENTS:component.update(text='A useful long explanation that wraps across lines.',bind=None)
                    elif kind in BUTTON_COMPONENTS:component.update(label='Save',action='recalculate')
                    else:
                        binding={'number':'amount','items':'history','text':'entry','boolean':'enabled'}[field_type]
                        component.update(label='Example control',bind=binding)
                        if field_type=='number':component['unit']='kg'
                        if kind in GOAL_COMPONENTS:component['goal']=100
                    sample=copy.deepcopy(app);sample.pop('pages',None);sample['components']=[component]
                    if field_type=='boolean':sample['state']['fields'].append(dict(id='enabled',type='boolean',value=True))
                    fields(sample)['history']['value']=[dict(id='i_'+str(i),label='Entry '+str(i)+': '+str(i+1),checked=False) for i in range(4)]
                    validate_app(sample)
                    index=self.app.device.registry.index(app);self.app.device.registry[index]=sample
                    self.app.device.open_app(sample['id']);self.app.screen.scroll=0
                    with self.subTest(theme=theme,component=kind):self.paint(100)
                    self.app.device.registry[index]=app
