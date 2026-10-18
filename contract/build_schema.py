"""Generate Gemini and runtime schemas from the same bounded component catalog."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def obj(properties):return {'type':'object','additionalProperties':False,'required':list(properties),'properties':properties}
def enum(*values):return {'type':'string','enum':list(values)}
def string(size=120):return {'type':'string','minLength':1,'maxLength':size}
def ident():return {'type':'string','pattern':'^[a-z][a-z0-9_]{0,31}$','maxLength':32}
def array(items,maximum,minimum=0):return {'type':'array','items':items,'minItems':minimum,'maxItems':maximum}
def branch(tag,properties):return obj({'type':enum(*(tag if isinstance(tag,tuple) else (tag,))),**properties})

TEXT_COMPONENTS=('text','callout','hero_banner','accordion','summary_footer')
NUMBER_COMPONENTS=('number','stepper','tally_pad','unit_converter','randomizer','timer','pacer','number_input')
GOAL_COMPONENTS=('progress','bar_gauge','arc_gauge','split_bar','delta_card','quick_chips','xy_pad')
TOGGLE_COMPONENTS=('toggle',)
ITEM_COMPONENTS=('list','segmented','stat_grid','tag_chips','inventory_list','habit_grid','key_value_log',
                 'bar_chart','data_table','matrix_2x2','date_strip','phase_bar','timeline_steps','deck_card','tabs')
INPUT_COMPONENTS=('input',)
BUTTON_COMPONENTS=('button','confirm_button')
GAME_COMPONENTS=('choice_game',)
ASSET={'type':'string','minLength':1,'maxLength':64,'pattern':'^[a-z][a-z0-9-]*$'}
ASSET_COMPONENTS=('illustration',)
GAME_CHOICE=obj({'id':ident(),'label':string(16),'icon':ASSET,
                 'beats':array(ident(),4,1)})
GAME_BINDINGS={'player':ident(),'opponent':ident(),'wins':ident(),'losses':ident(),'draws':ident(),
               'choices':array(GAME_CHOICE,5,3)}

ITEM=obj({'id':ident(),'label':string(120),'checked':{'type':'boolean'}})
ITEM['properties']['icon']=ASSET
VALUE={'anyOf':[{'type':'string','maxLength':2000},{'type':'number'}, {'type':'boolean'},array(ITEM,100)]}
FIELDS={'anyOf':[
    branch('text',{'id':ident(),'value':{'type':'string','maxLength':2000}}),
    branch('number',{'id':ident(),'value':{'type':'number'},'min':{'type':'number'},'max':{'type':'number'}}),
    branch('boolean',{'id':ident(),'value':{'type':'boolean'}}),
    branch('items',{'id':ident(),'value':array(ITEM,100)}),
]}
COMPONENTS={'anyOf':[
    branch(TEXT_COMPONENTS,{'id':ident(),'text':{'type':'string','maxLength':300},'bind':{'type':['string','null'],'maxLength':32}}),
    branch(NUMBER_COMPONENTS,{'id':ident(),'label':string(80),'bind':ident(),'unit':{'type':'string','maxLength':24}}),
    branch(GOAL_COMPONENTS,{'id':ident(),'label':string(80),'bind':ident(),'goal':{'type':'number','minimum':0},'unit':{'type':'string','maxLength':24}}),
    branch(TOGGLE_COMPONENTS,{'id':ident(),'label':string(80),'bind':ident()}),
    branch(ITEM_COMPONENTS,{'id':ident(),'label':string(80),'bind':ident()}),
    branch(INPUT_COMPONENTS,{'id':ident(),'label':string(80),'bind':ident()}),
    branch(BUTTON_COMPONENTS,{'id':ident(),'label':string(80),'action':ident()}),
    branch(GAME_COMPONENTS,{'id':ident(),'label':string(80),'bind':ident(),**GAME_BINDINGS}),
    branch(ASSET_COMPONENTS,{'id':ident(),'icon':ASSET,'label':string(120),'size':enum('small','medium','large')}),
]}
for component in COMPONENTS['anyOf']:
    component['properties']['icon']=ASSET
    if 'bind' in component['properties']:component['properties']['on_change']=ident()

OPERAND={'anyOf':[obj({'field':ident()}),obj({'literal':{'type':'number'}})]}
BASE_OPERATIONS={'anyOf':[
    obj({'action':enum('set'),'target':ident(),'value':VALUE}),
    obj({'action':enum('increment'),'target':ident(),'amount':{'type':'number','minimum':-1000000,'maximum':1000000}}),
    obj({'action':enum('toggle'),'target':ident()}),
    obj({'action':enum('append'),'target':ident(),'source':ident()}),
    obj({'action':enum('clear'),'target':ident()}),
    obj({'action':enum('remove_checked'),'target':ident()}),
    obj({'action':enum('calculate'),'target':ident(),'operator':enum('add','subtract','multiply','divide'),
         'left':OPERAND,'right':OPERAND}),
    obj({'action':enum('append_record'),'target':ident(),'source':ident(),'amount':ident()}),
    obj({'action':enum('sum_records'),'target':ident(),'source':ident()}),
    obj({'action':enum('play_choice'),'target':ident(),'choice':ident(),**GAME_BINDINGS}),
]}
OPERATIONS={'anyOf':BASE_OPERATIONS['anyOf']+[
    obj({'action':enum('batch'),'steps':array(BASE_OPERATIONS,8,1)})]}
ACTIONS={'anyOf':[obj({'id':ident(),**schema['properties']}) for schema in OPERATIONS['anyOf']]}
PAGE=obj({'id':ident(),'title':string(16),'components':array(ident(),24,1)})
APP=obj({'id':ident(),'module':enum('composed'),'title':string(16),
         'state':obj({'fields':array(FIELDS,32)}),'components':array(COMPONENTS,24,1),'actions':array(ACTIONS,32)})
# Optional keeps existing saved apps and fixtures valid; new apps can have real pages.
APP['properties']['pages']=array(PAGE,4,1)
APP['properties']['icon']=ASSET

def turn(intent,op,extra):
    return obj({'schema_version':{'type':'integer','minimum':2,'maximum':2},'intent':enum(intent),'op':enum(op),'say':string(1200),**extra})
TURN={'anyOf':[
    turn('create_app','propose',{'app':APP}),
    turn('update_app','mutate',{'app_id':ident(),'actions':array(OPERATIONS,32,1)}),
    turn('navigate','navigate',{'destination':enum('agent','apps','settings','notes','clock','calculator','app'),'app_id':{'type':['string','null'],'maxLength':32}}),
    {**turn('message','say',{}),'properties':{**turn('message','say',{})['properties'],'intent':enum('message','create_app','update_app','navigate')}},
]}
SCHEMAS={'app.schema.json':APP,'turn.schema.json':TURN,'turn.strict.json':obj({'turn':TURN})}

def gemini_schema(value):
    # Vertex rejects this union when combined with all of its size/range bounds.
    # Keep the closed shape/type/tag constraints at generation time; enforce every
    # bound and cross-reference with the complete schema before accepting a turn.
    if isinstance(value,list):return [gemini_schema(item) for item in value]
    if isinstance(value,dict):
        return {key:gemini_schema(item) for key,item in value.items()
                if key not in ('minLength','maxLength','pattern','minimum','maximum','minItems','maxItems')}
    return value

MODEL_SCHEMA=gemini_schema(SCHEMAS['turn.strict.json'])

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    for name,schema in {**SCHEMAS,'turn.gemini.json':MODEL_SCHEMA}.items():
        content=json.dumps(schema,indent=2)+'\n';path=ROOT/name
        if args.check:
            if not path.exists() or path.read_text()!=content:raise SystemExit('Regenerate '+name)
        else:path.write_text(content)

if __name__=='__main__':main()
