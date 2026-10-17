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
def branch(tag,properties):return obj({'type':enum(tag),**properties})

ITEM=obj({'id':ident(),'label':string(120),'checked':{'type':'boolean'}})
VALUE={'anyOf':[{'type':'string','maxLength':2000},{'type':'number'}, {'type':'boolean'},array(ITEM,100)]}
FIELDS={'anyOf':[
    branch('text',{'id':ident(),'value':{'type':'string','maxLength':2000}}),
    branch('number',{'id':ident(),'value':{'type':'number'},'min':{'type':'number'},'max':{'type':'number'}}),
    branch('boolean',{'id':ident(),'value':{'type':'boolean'}}),
    branch('items',{'id':ident(),'value':array(ITEM,100)}),
]}
COMPONENTS={'anyOf':[
    branch('text',{'id':ident(),'text':{'type':'string','maxLength':300},'bind':{'type':['string','null'],'maxLength':32}}),
    branch('number',{'id':ident(),'label':string(80),'bind':ident(),'unit':{'type':'string','maxLength':24}}),
    branch('progress',{'id':ident(),'label':string(80),'bind':ident(),'goal':{'type':'number','minimum':0},'unit':{'type':'string','maxLength':24}}),
    branch('toggle',{'id':ident(),'label':string(80),'bind':ident()}),
    branch('list',{'id':ident(),'label':string(80),'bind':ident()}),
    branch('input',{'id':ident(),'label':string(80),'bind':ident()}),
    branch('button',{'id':ident(),'label':string(80),'action':ident()}),
]}
OPERATIONS={'anyOf':[
    obj({'action':enum('set'),'target':ident(),'value':VALUE}),
    obj({'action':enum('increment'),'target':ident(),'amount':{'type':'number','minimum':-1000000,'maximum':1000000}}),
    obj({'action':enum('toggle'),'target':ident()}),
    obj({'action':enum('append'),'target':ident(),'source':ident()}),
    obj({'action':enum('clear'),'target':ident()}),
    obj({'action':enum('remove_checked'),'target':ident()}),
]}
ACTIONS={'anyOf':[obj({'id':ident(),**schema['properties']}) for schema in OPERATIONS['anyOf']]}
APP=obj({'id':ident(),'module':enum('composed'),'title':string(48),
         'state':obj({'fields':array(FIELDS,32)}),'components':array(COMPONENTS,24,1),'actions':array(ACTIONS,32)})

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
