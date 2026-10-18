"""Validate data and execute only the fixed component actions; never model code."""
import copy
import json
import math
import random
import uuid
from jsonschema import Draft202012Validator
from .build_schema import (BUTTON_COMPONENTS, FIELDS, GOAL_COMPONENTS, INPUT_COMPONENTS,
                           ITEM_COMPONENTS, NUMBER_COMPONENTS, OPERATIONS, SCHEMAS,
                           TEXT_COMPONENTS, TOGGLE_COMPONENTS, GAME_COMPONENTS, ASSET_COMPONENTS)
from .asset_catalog import resolve as resolve_asset

class ContractError(ValueError):pass

_VALIDATORS={name:Draft202012Validator(schema) for name,schema in SCHEMAS.items()}
_OPERATION=Draft202012Validator(OPERATIONS)
_FIELD=Draft202012Validator(FIELDS)

def finite(value):
    if isinstance(value,float) and not math.isfinite(value):raise ContractError('Numbers must be finite')
    if isinstance(value,dict):
        for item in value.values():finite(item)
    elif isinstance(value,list):
        for item in value:finite(item)

def check(validator,value):
    finite(value)
    error=next(validator.iter_errors(value),None)
    if error:
        path='.'.join(map(str,error.absolute_path)) or 'response'
        raise ContractError('Invalid contract at '+path)

def unique(values,label):
    ids=[value['id'] for value in values]
    if len(ids)!=len(set(ids)):raise ContractError('Duplicate '+label+' IDs')

def fields(app):return {field['id']:field for field in app['state']['fields']}

def validate_asset(name):
    if resolve_asset(name) is None:raise ContractError('Unknown offline asset: '+str(name))

def validate_game(spec,state,target):
    bindings=[target]+[spec[key] for key in ('player','opponent','wins','losses','draws')]
    if len(set(bindings))!=len(bindings):raise ContractError('Game state bindings must be distinct')
    for key in (target,spec['player'],spec['opponent']):
        if state.get(key,{}).get('type')!='text':raise ContractError('Game moves and result require text fields')
    choices=spec['choices'];unique(choices,'choice');ids={c['id'] for c in choices}
    if ids=={'rock','paper','scissors'}:
        expected={'rock':{'scissors'},'paper':{'rock'},'scissors':{'paper'}}
        if any(set(c['beats'])!=expected[c['id']] for c in choices):
            raise ContractError('Rock paper scissors must use its standard rules')
    for choice in choices:
        validate_asset(choice['icon'])
        beats=choice['beats']
        if len(set(beats))!=len(beats) or not set(beats)<=ids-{choice['id']}:
            raise ContractError('Game rules reference duplicate, self, or unknown choices')
        for other in choices:
            if other['id']!=choice['id'] and ((other['id'] in beats)==(choice['id'] in other['beats'])):
                raise ContractError('Each pair of game choices must have exactly one winner')
    for key in (spec['player'],spec['opponent']):
        if state[key]['value'] not in ids|{''}:raise ContractError('Game move is not a declared choice')
    if state[target]['value'] not in ('','win','loss','draw'):raise ContractError('Unknown game outcome')
    player=state[spec['player']]['value'];opponent=state[spec['opponent']]['value'];outcome=state[target]['value']
    if outcome:
        if not player or not opponent:raise ContractError('A completed round requires both moves')
        expected='draw' if player==opponent else 'win' if opponent in next(c['beats'] for c in choices if c['id']==player) else 'loss'
        if outcome!=expected:raise ContractError('Game outcome does not match its declared rules')
    elif player or opponent:raise ContractError('Game moves require a completed round')
    for key in ('wins','losses','draws'):
        field=state.get(spec[key],{})
        if field.get('type')!='number' or field['min']!=0 or field['max']<1 or int(field['value'])!=field['value']:
            raise ContractError('Game scores require nonnegative whole-number fields starting at zero')

def validate_operation(action,state):
    check(_OPERATION,action)
    if action['action']=='batch':
        for step in action['steps']:validate_operation(step,state)
        return
    if action['action']=='play_choice':
        validate_game(action,state,action['target'])
        if action['choice'] not in {c['id'] for c in action['choices']}:
            raise ContractError('Selected game choice does not exist')
        return
    target=state.get(action['target'])
    if target is None:raise ContractError('Action targets an unknown state field')
    kind=action['action'];typ=target['type']
    allowed={'increment':('number',),'toggle':('boolean',),'append':('items',),
             'clear':('text','items'),'remove_checked':('items',),'set':('text','number','boolean','items'),
             'calculate':('number',),'append_record':('items',),'sum_records':('number',)}
    if typ not in allowed[kind]:raise ContractError('Action is incompatible with its target field')
    if kind=='sum_records' and state.get(action['source'],{}).get('type')!='items':
        raise ContractError('Record sum source must reference an items field')
    if kind=='calculate':
        for operand in (action['left'],action['right']):
            if 'field' in operand and state.get(operand['field'],{}).get('type')!='number':
                raise ContractError('Calculation operands must reference number fields')
    if kind=='append_record' and state.get(action['amount'],{}).get('type')!='number':
        raise ContractError('Record amount must reference a number field')
    if kind in ('append','append_record') and state.get(action['source'],{}).get('type')!='text':
        raise ContractError('Append source must be a text field')
    if kind=='set':
        candidate=copy.deepcopy(target);candidate['value']=action['value']
        check(_FIELD,candidate)
        validate_field(candidate)

def validate_field(field):
    if field['type']=='number' and not field['min']<=field['value']<=field['max']:
        raise ContractError('Number must be within its field bounds')
    if field['type']=='items':
        unique(field['value'],'item')
        for item in field['value']:
            if 'icon' in item:validate_asset(item['icon'])

def validate_app(app):
    check(_VALIDATORS['app.schema.json'],app)
    if 'icon' in app:validate_asset(app['icon'])
    unique(app['state']['fields'],'field');unique(app['components'],'component');unique(app['actions'],'action')
    state=fields(app);actions={action['id']:action for action in app['actions']}
    for field in state.values():validate_field(field)
    for action in actions.values():validate_operation({k:v for k,v in action.items() if k!='id'},state)
    types={
        **{k:'text' for k in TEXT_COMPONENTS+INPUT_COMPONENTS},
        **{k:'number' for k in NUMBER_COMPONENTS+GOAL_COMPONENTS},
        **{k:'boolean' for k in TOGGLE_COMPONENTS},
        **{k:'items' for k in ITEM_COMPONENTS},
        **{k:'text' for k in GAME_COMPONENTS},
    }
    for component in app['components']:
        typ=component['type']
        if 'icon' in component:validate_asset(component['icon'])
        if typ in ASSET_COMPONENTS:continue
        if typ in GAME_COMPONENTS:validate_game(component,state,component['bind'])
        if component.get('on_change') and component['on_change'] not in actions:
            raise ContractError('Component change handler references an unknown action')
        if typ in BUTTON_COMPONENTS:
            if component['action'] not in actions:raise ContractError('Button references an unknown action')
        else:
            binding=component.get('bind')
            if typ in TEXT_COMPONENTS and binding is None:
                if not component['text'].strip():raise ContractError('Literal text must not be blank')
                continue
            if state.get(binding,{}).get('type')!=types[typ]:raise ContractError('Component binding has an incompatible state type')
            if typ in GOAL_COMPONENTS and (component['goal']<=0 or component['goal']>state[binding]['max']):
                raise ContractError('Progress goal must be positive and within its field bounds')
    if 'pages' in app:
        unique(app['pages'],'page')
        component_ids={c['id'] for c in app['components']}
        visible=set()
        for page in app['pages']:
            refs=page['components']
            if len(refs)!=len(set(refs)) or not set(refs)<=component_ids:
                raise ContractError('Page references missing or duplicate components')
            visible.update(refs)
        if visible!=component_ids:raise ContractError('Every component must be reachable from a page')
    return app

def apply_operations(app,operations,_reactions=True):
    """Apply the entire batch to a copy; the caller commits it only on success."""
    validate_app(app);result=copy.deepcopy(app);state=fields(result)
    expanded=[]
    for action in operations:
        validate_operation(action,state)
        expanded.extend(action['steps'] if action['action']=='batch' else [action])
    if len(expanded)>256:raise ContractError('Too many action steps')
    for action in expanded:
        target=state[action['target']];kind=action['action']
        if kind=='set':target['value']=copy.deepcopy(action['value'])
        elif kind=='play_choice':
            choices={c['id']:c for c in action['choices']}
            player=action['choice'];opponent=random.choice(list(choices))
            outcome='draw' if player==opponent else 'win' if opponent in choices[player]['beats'] else 'loss'
            target['value']=outcome
            state[action['player']]['value']=player;state[action['opponent']]['value']=opponent
            score=state[action[{'win':'wins','loss':'losses','draw':'draws'}[outcome]]]
            if score['value']+1>score['max']:raise ContractError('Score limit reached. Start a new match.')
            score['value']+=1
        elif kind=='increment':target['value']=max(target['min'],min(target['max'],target['value']+action['amount']))
        elif kind=='toggle':target['value']=not target['value']
        elif kind=='clear':target['value']=[] if target['type']=='items' else ''
        elif kind=='remove_checked':target['value']=[item for item in target['value'] if not item['checked']]
        elif kind=='sum_records':
            values=[]
            for item in state[action['source']]['value']:
                try:value=float(item['label'].rsplit(': ',1)[1])
                except (ValueError,IndexError):raise ContractError('Keep each record in label: number format.')
                if not math.isfinite(value):raise ContractError('Record values must be finite.')
                values.append(value)
            value=sum(values)
            if not math.isfinite(value) or not target['min']<=value<=target['max']:
                raise ContractError('Record total exceeds its field limits.')
            target['value']=value
        elif kind=='calculate':
            def operand(spec):return state[spec['field']]['value'] if 'field' in spec else spec['literal']
            left,right=operand(action['left']),operand(action['right'])
            if action['operator']=='divide' and right==0:raise ContractError('Cannot divide by zero.')
            value={'add':lambda:left+right,'subtract':lambda:left-right,
                   'multiply':lambda:left*right,'divide':lambda:left/right}[action['operator']]()
            if not math.isfinite(value):raise ContractError('Calculation result is not finite.')
            if not target['min']<=value<=target['max']:raise ContractError('Calculation exceeds its field limits.')
            target['value']=value
        elif kind in ('append','append_record'):
            source=state[action['source']];label=source['value'].strip()
            if not label:raise ContractError('Enter a label before saving.')
            if label:
                if kind=='append_record':label+=': '+format(state[action['amount']]['value'],'.10g')
                if len(label)>120:raise ContractError('Keep each item to 120 characters or fewer.')
                if len(target['value'])>=100:raise ContractError('This list is full. Remove an item first.')
                target['value'].append({'id':'item_'+uuid.uuid4().hex[:20],'label':label,'checked':False})
                source['value']=''
    validate_app(result)
    if _reactions:
        before=fields(app)
        changed={name for name,field in state.items() if field['value']!=before[name]['value']}
        reactions={c['on_change'] for c in app['components'] if c.get('bind') in changed and c.get('on_change')}
        if reactions:
            actions={a['id']:a for a in app['actions']}
            followups=[{k:v for k,v in actions[name].items() if k!='id'} for name in sorted(reactions)]
            result=apply_operations(result,followups,_reactions=False)
    return result

def validate_turn(turn,registry=()):
    check(_VALIDATORS['turn.schema.json'],turn)
    if not turn['say'].strip():raise ContractError('Response text must not be blank')
    if turn['op']=='navigate':
        destination=turn['destination']
        if destination=='app':
            if not turn['app_id'] or not any(app.get('id')==turn['app_id'] and app.get('module')=='composed' for app in registry):
                raise ContractError('Navigation targets an unknown app')
        elif turn['app_id'] is not None:raise ContractError('Named destinations must not include an app ID')
    elif turn['op']=='propose':
        validate_app(turn['app'])
        if any(app.get('id')==turn['app']['id'] for app in registry):raise ContractError('App ID already exists')
        if turn['app']['id'] in ('omni','settings','notes','clock','calculator'):raise ContractError('App ID is reserved')
    elif turn['op']=='mutate':
        target=next((app for app in registry if app.get('id')==turn['app_id']),None)
        if target is None or target.get('module')!='composed':raise ContractError('Update targets an unknown generated app')
        apply_operations(target,turn['actions'])
    return turn

def parse_response(text,registry=()):
    if not isinstance(text,str):raise ContractError('Response must be JSON text')
    if len(text)>65536:raise ContractError('Response exceeds the size limit')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ContractError('Duplicate JSON property')
            result[key]=value
        return result
    try:body=json.loads(text,object_pairs_hook=pairs,parse_constant=lambda value: (_ for _ in ()).throw(ContractError('Non-finite JSON number')))
    except (json.JSONDecodeError,TypeError) as error:raise ContractError('Response must be one JSON object') from error
    check(_VALIDATORS['turn.strict.json'],body)
    return validate_turn(body['turn'],registry)


def message(text):return {'schema_version':2,'intent':'message','op':'say','say':text}


def navigation(destination,app_id=None):
    return {'schema_version':2,'intent':'navigate','op':'navigate','say':'Opening '+('Omni' if destination=='agent' else 'your apps' if destination=='apps' else destination)+'.','destination':destination,'app_id':app_id}


def command_words(text):
    """Normalize only command syntax, not dictated note/list content."""
    import re
    command=' '.join(re.findall(r"[a-z0-9]+",text.lower()))
    command=re.sub(r'^(?:(?:hey |okay |ok )?omni |please |can you |could you |would you |will you |'
                   r'i want you to |i would like you to |i d like you to |let s )+', '', command)
    return re.sub(r'(?: please| for me| thanks| thank you)+$', '', command)


def preview_navigation(text,registry=()):
    """Match complete navigation commands; ambiguous targets need the model."""
    import re
    command=command_words(text)
    if command in ('back','go back','take me back','return','exit app','close app','close this app'):
        return navigation('apps')
    match=re.fullmatch(r'(?:navigate(?: me)?(?: to)?|take me(?: to)?|bring me(?: to)?|get me to|'
                       r'go(?: back)?(?: to| into)?|head to|jump to|show(?: me)?|open(?: up)?|'
                       r'launch|start|load|bring up|pull up|return(?: to)?|back to|switch(?: over)? to) (.+)',command)
    target=match[1] if match else command
    target=re.sub(r'^(?:the |my )','',target)
    variants={target,re.sub(r' (?:page|screen|app|application|view)$','',target)}
    names={'agent':('agent','main agent','home','home page','home screen','main','main screen',
                    'omni','omni agent','assistant','main assistant','agent home','main agent screen'),
           'apps':('apps','applications','app selection','app selector','app wheel','wheel','launcher',
                   'app launcher','app drawer','my apps','all apps','application selector'),
           'settings':('settings','setting','preferences','device settings','system settings'),
           'notes':('notes','note','notebook','notepad'),
           'clock':('clock','time','digital clock'),
           'calculator':('calculator','calc','math','calculation')}
    matches=set()
    for destination,aliases in names.items():
        if variants.intersection(aliases):matches.add((destination,None))
    for app in registry:
        if app.get('module')!='composed':continue
        title=' '.join(re.findall(r"[a-z0-9]+",app.get('title','').lower()))
        identifier=app.get('id','').replace('_',' ')
        if variants.intersection({title,identifier}-{''}):matches.add(('app',app['id']))
    if len(matches)!=1:return None
    destination,app_id=matches.pop()
    return navigation(destination,app_id)
