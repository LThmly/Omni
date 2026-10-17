"""Validate data and execute only the fixed component actions; never model code."""
import copy
import json
import math
import uuid
from jsonschema import Draft202012Validator
from .build_schema import FIELDS, OPERATIONS, SCHEMAS

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

def validate_operation(action,state):
    check(_OPERATION,action)
    target=state.get(action['target'])
    if target is None:raise ContractError('Action targets an unknown state field')
    kind=action['action'];typ=target['type']
    allowed={'increment':('number',),'toggle':('boolean',),'append':('items',),
             'clear':('text','items'),'remove_checked':('items',),'set':('text','number','boolean','items')}
    if typ not in allowed[kind]:raise ContractError('Action is incompatible with its target field')
    if kind=='append' and state.get(action['source'],{}).get('type')!='text':
        raise ContractError('Append source must be a text field')
    if kind=='set':
        candidate=copy.deepcopy(target);candidate['value']=action['value']
        check(_FIELD,candidate)
        validate_field(candidate)

def validate_field(field):
    if field['type']=='number' and not field['min']<=field['value']<=field['max']:
        raise ContractError('Number must be within its field bounds')
    if field['type']=='items':unique(field['value'],'item')

def validate_app(app):
    check(_VALIDATORS['app.schema.json'],app)
    unique(app['state']['fields'],'field');unique(app['components'],'component');unique(app['actions'],'action')
    state=fields(app);actions={action['id']:action for action in app['actions']}
    for field in state.values():validate_field(field)
    for action in actions.values():validate_operation({k:v for k,v in action.items() if k!='id'},state)
    types={'text':'text','input':'text','number':'number','progress':'number','toggle':'boolean','list':'items'}
    for component in app['components']:
        typ=component['type']
        if typ=='button':
            if component['action'] not in actions:raise ContractError('Button references an unknown action')
        else:
            binding=component.get('bind')
            if typ=='text' and binding is None:
                if not component['text'].strip():raise ContractError('Literal text must not be blank')
                continue
            if state.get(binding,{}).get('type')!=types[typ]:raise ContractError('Component binding has an incompatible state type')
            if typ=='progress' and (component['goal']<=0 or component['goal']>state[binding]['max']):
                raise ContractError('Progress goal must be positive and within its field bounds')
    return app

def apply_operations(app,operations):
    """Apply the entire batch to a copy; the caller commits it only on success."""
    validate_app(app);result=copy.deepcopy(app);state=fields(result)
    for action in operations:
        validate_operation(action,state)
        target=state[action['target']];kind=action['action']
        if kind=='set':target['value']=copy.deepcopy(action['value'])
        elif kind=='increment':target['value']=max(target['min'],min(target['max'],target['value']+action['amount']))
        elif kind=='toggle':target['value']=not target['value']
        elif kind=='clear':target['value']=[] if target['type']=='items' else ''
        elif kind=='remove_checked':target['value']=[item for item in target['value'] if not item['checked']]
        elif kind=='append':
            source=state[action['source']];label=source['value'].strip()
            if label:
                if len(label)>120:raise ContractError('Keep each item to 120 characters or fewer.')
                if len(target['value'])>=100:raise ContractError('This list is full. Remove an item first.')
                target['value'].append({'id':'item_'+uuid.uuid4().hex[:20],'label':label,'checked':False})
                source['value']=''
    validate_app(result)
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
