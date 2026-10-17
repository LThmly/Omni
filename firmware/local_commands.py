"""Fast, explicit device commands. No network, fuzzy intent guessing, or model code."""
import ast
from dataclasses import dataclass
import datetime
import math
import operator
import re
from contract.runtime import command_words, message, preview_navigation, fields, validate_turn, ContractError


@dataclass
class LocalCommand:
    turn: dict
    effect: dict | None = None


def theme_command(text,current):
    command=command_words(text).replace('night mode','dark mode').replace('day mode','light mode')
    subject=r'(?:(?:the )?(?:system )?(?:color scheme|colour scheme|theme|appearance|mode))'
    if re.fullmatch(r'(?:toggle|switch|change) '+subject,command) or command in (
            'switch between light and dark mode','switch between dark and light mode'):
        return 'light' if current=='dark' else 'dark'
    match=re.fullmatch(r'turn (light|dark) mode (on|off)',command)
    if match:return match[1] if match[2]=='on' else ('light' if match[1]=='dark' else 'dark')
    match=re.fullmatch(r'(?P<prefix>(?:switch|change|set)(?: '+subject+r')? to |'
                       r'(?:enable|use|activate|turn on|go to) |set )?'
                       r'(?P<theme>light|dark)(?P<suffix> mode| theme| color scheme| colour scheme)?',command)
    if match and (match['prefix'] or match['suffix']):return match['theme']
    if command in ('disable dark mode','turn off dark mode'):return 'light'
    if command in ('disable light mode','turn off light mode'):return 'dark'
    return None

def calculate(expression):
    """Arithmetic only; reject names, calls, powers and unbounded expressions."""
    if len(expression) > 80:
        raise ValueError('Expression too long')
    tree = ast.parse(expression, mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 64:
        raise ValueError('Expression too long')
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
    def visit(node):
        if isinstance(node, ast.Expression): return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float): return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in (ast.UAdd, ast.USub):
            return visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            return binary[type(node.op)](visit(node.left), visit(node.right))
        raise ValueError('Unsupported expression')
    value = float(visit(tree))
    if not math.isfinite(value): raise ValueError('Invalid result')
    return format(value, '.12g')


_SMALL=dict(zip(('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen').split(),range(20)))
_TENS=dict(zip('twenty thirty forty fifty sixty seventy eighty ninety'.split(),range(20,100,10)))


def _under_hundred(words):
    if len(words)==1 and words[0] in _SMALL:return _SMALL[words[0]]
    if len(words)==1 and words[0] in _TENS:return _TENS[words[0]]
    if len(words)==2 and words[0] in _TENS and words[1] in _SMALL and 1<=_SMALL[words[1]]<=9:
        return _TENS[words[0]]+_SMALL[words[1]]
    raise ValueError('Not a number')


def _integer(words):
    for scale,name in ((1000,'thousand'),(100,'hundred')):
        if name in words:
            if words.count(name)!=1:raise ValueError('Not a number')
            i=words.index(name);left=_integer(words[:i]);right=words[i+1:]
            if not 1<=left<(1000 if scale==1000 else 10):raise ValueError('Not a number')
            if right[:1]==['and']:right=right[1:]
            tail=_integer(right) if right else 0
            if tail>=scale:raise ValueError('Not a number')
            return left*scale+tail
    return _under_hundred(words)


def spoken_expression(text):
    text=text.lower().strip().rstrip('?!.')
    for phrase,symbol in (('multiplied by','*'),('divided by','/'),('times','*'),
                          ('plus','+'),('minus','-'),('over','/'),('negative','-')):
        text=re.sub(r'\b'+phrase+r'\b',symbol,text)
    parts=re.split(r'([+*/()\-])',text);out=[]
    for part in parts:
        part=part.strip()
        if not part:continue
        if part in '+-*/()':out.append(part);continue
        if re.fullmatch(r'\d+(?:\.\d+)?',part):out.append(part);continue
        words=part.split()
        if words.count('point')==1:
            i=words.index('point');digits=words[i+1:]
            if not digits or any(word not in _SMALL or _SMALL[word]>9 for word in digits):raise ValueError('Not a decimal')
            out.append(str(_integer(words[:i]))+'.'+''.join(str(_SMALL[word]) for word in digits))
        else:out.append(str(_integer(words)))
    return ''.join(out)


def _setting(key,value,say):
    return LocalCommand(message(say),dict(kind='preference',key=key,value=value))


def _content_command(text):
    return re.sub(r"^(?:(?:hey |okay |ok )?omni |please |can you |could you |would you |will you |"
                  r"i want you to |i would like you to |i'd like you to |let's )+",'',text.strip(),flags=re.I)


def _generated(text,registry):
    """Invoke registered buttons or append through an existing list action."""
    raw=text.strip().rstrip('.!?')
    raw=_content_command(raw)
    candidates=[]
    button=re.fullmatch(r'(?:press|tap|run|activate) (?:the )?(.+?)(?: button| action)? (?:in|on|for) (?:the |my )?(.+)',raw,re.I)
    addition=re.fullmatch(r'(?:add|append|put) (.+) (?:to|on) (?:the |my )?(.+)',raw,re.I)
    if not button and not addition:return None
    label,target=button.groups() if button else addition.groups()
    target=command_words(target)
    for app in registry:
        if app.get('module')!='composed':continue
        names={command_words(app['title']),app['id'].replace('_',' ')}
        aliases=names|{name+' app' for name in names}
        if any(c['type']=='list' for c in app['components']):aliases|={name+' list' for name in names}
        if target not in aliases:continue
        if button:
            for component in app['components']:
                if component['type']!='button' or command_words(component['label'])!=command_words(label):continue
                action=next(a for a in app['actions'] if a['id']==component['action'])
                operations=[{key:value for key,value in action.items() if key!='id'}]
                candidates.append((app,operations,'Running '+component['label']+' in '+app['title']+'.'))
        else:
            state=fields(app)
            for action in app['actions']:
                if action['action']!='append' or len(label)>2000:continue
                source=state.get(action['source'])
                if not source or source['type']!='text':continue
                operations=[dict(action='set',target=action['source'],value=label),
                            {key:value for key,value in action.items() if key!='id'}]
                candidates.append((app,operations,'Adding that to '+app['title']+'.'))
    if len(candidates)!=1:return None
    app,operations,say=candidates[0]
    turn=dict(schema_version=2,intent='update_app',op='mutate',say=say,app_id=app['id'],actions=operations)
    try:validate_turn(turn,registry)
    except ContractError as error:return LocalCommand(message(str(error)))
    return LocalCommand(turn)


def match_command(text,prefs,registry,now=None):
    """Return a complete local turn and optional device-owned effect, or None."""
    c=command_words(text)
    theme=theme_command(text,prefs['theme'])
    if theme:return _setting('theme',theme,'Switching to '+theme+' mode.')
    motion=r'(?:animations?|motion|motion effects)'
    if re.fullmatch(r'(?:enable|turn on|restore) '+motion,c) or re.fullmatch(r'turn '+motion+r' on',c) or c in ('disable reduced motion','turn off reduced motion'):
        return _setting('motion',True,'Animations enabled.')
    if re.fullmatch(r'(?:disable|turn off|stop) '+motion,c) or re.fullmatch(r'turn '+motion+r' off',c) or c in ('enable reduced motion','turn on reduced motion','reduce motion'):
        return _setting('motion',False,'Reduced motion enabled.')
    if re.fullmatch(r'toggle '+motion,c):return _setting('motion',not prefs['motion'],'Switching animation preference.')
    if c in ('make the text bigger','make text bigger','increase text size','increase font size','larger text','bigger text','use large text','large text','set text size to large','make the font bigger','make font bigger','enable large text','turn on large text'):
        return _setting('text_scale',1.15,'Switching to larger text.')
    if c in ('make the text smaller','make text smaller','decrease text size','decrease font size','normal text','use normal text','standard text','reset text size','set text size to normal','set text size to standard','make the font smaller','make font smaller','disable large text','turn off large text'):
        return _setting('text_scale',1,'Switching to standard text.')
    if c in ('toggle clock format','toggle time format','switch clock format'):
        return _setting('clock24',not prefs['clock24'],'Switching clock format.')
    clock=re.fullmatch(r'(?:use|enable|switch to|set (?:the )?clock to) (12|twelve|24|twenty four) (?:hour|hour clock|hour time|hour format|hour time format)',c)
    if clock or c in ('use military time','enable military time','turn on military time','disable military time','turn off military time','use am pm time'):
        use24=clock[1] in ('24','twenty four') if clock else c in ('use military time','enable military time','turn on military time')
        return _setting('clock24',use24,'Using '+('24' if use24 else '12')+'-hour time.')
    wait=re.fullmatch(r'(?:set|change) (?:the )?(?:preview wait|demo wait|preview delay) to (three|3|ten|10|twenty|20) seconds',c)
    if wait:
        value={'three':3,'ten':10,'twenty':20}.get(wait[1]) or int(wait[1])
        return _setting('wait_seconds',value,'Preview wait set to '+str(value)+' seconds.')
    now=now or datetime.datetime.now()
    if c in ('what time is it','what is the time','tell me the time','tell me what time it is','current time','time now','show me the time','give me the time','what s the time','what is the current time','what s the current time'):
        return LocalCommand(message(now.strftime('It is %H:%M.' if prefs['clock24'] else 'It is %I:%M %p.')))
    if c in ('what is the date','what s the date','what is today s date','what day is it','what day is today','tell me the date','today s date','current date','show me the date','what s today s date'):
        return LocalCommand(message(now.strftime('Today is %A, %B %d, %Y.')))
    if c in ('read my notes','read the notes','what is in my notes','show me what s in my notes'):
        note=next((a for a in registry if a['id']=='notes'),None)
        content=note['state'].get('text','') if note else ''
        say=(content[:1050]+'… Open Notes to see the rest.') if len(content)>1050 else content
        return LocalCommand(message(say or 'Your notes are empty.'))
    raw=_content_command(text)
    note=re.fullmatch(r'(?:take a note|make a note|write a note|save a note|add a note|note down|remember this|add to (?:my )?notes)(?: that)?[ :]+(.+)',raw,re.I)
    if note and len(note[1])<=2000 and any(a['id']=='notes' for a in registry):
        return LocalCommand(message('Adding that to Notes.'),dict(kind='note',text=note[1]))
    calculation=re.fullmatch(r"(?:calculate|compute|what is|what's|what s|work out) (.+)",raw,re.I)
    if calculation:
        try:
            expression=spoken_expression(calculation[1])
            if not any(op in expression for op in '+-*/'):raise ValueError('No arithmetic')
            answer=calculate(expression)
        except ZeroDivisionError:return LocalCommand(message('Division by zero is undefined.'))
        except (ValueError,SyntaxError,OverflowError):pass
        else:return LocalCommand(message('The answer is '+answer+'.'),dict(kind='calculation',value=answer))
    generated=_generated(text,registry)
    if generated:return generated
    navigate=preview_navigation(text,registry)
    if navigate:return LocalCommand(navigate)
    return None
