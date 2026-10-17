"""Shared desktop/Pi UI. The simulator and kiosk use the same input and paint path."""
from __future__ import annotations

import ast
import copy
import datetime
import json
import math
import operator
import random
import sys
import time
from pathlib import Path

import pygame
import phone as legacy
from logic import Device
from transcript import TranscriptAnimator

BUILTINS = (
    ('omni', 'omni', 'home'), ('settings', 'settings', 'settings'),
    ('notes', 'notes', 'notes'), ('clock', 'clock', 'clock'),
    ('calculator', 'calculator', 'calculator'),
)
DEFAULTS = dict(theme='dark', motion=True, text_scale=1, wait_seconds=10, clock24=True, show_input=True)
SETTINGS_COUNT = 6
CX, CY, RADIUS, STEP, FOCUS = -8, 686, 328, math.radians(22), math.radians(-42)
VOICE = pygame.Rect(192, 626, 96, 76)


def default_apps():
    return [dict(id=id, title=title, module=module, state={'text': ''} if module == 'notes' else {})
            for id, title, module in BUILTINS]


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


def demo_app(request, registry):
    """Local stand-in for a model response, shared by simulator and kiosk."""
    text = request.strip()
    lower = text.lower()
    if any(word in lower for word in ('milk', 'shop', 'grocer')):
        app = dict(id='shopping', title='shopping', module='checklist',
                   state={'cursor': 0, 'items': [{'label': 'Milk', 'checked': False}]})
    elif any(word in lower for word in ('water', 'hydrat', 'ounce')):
        app = dict(id='water', title='hydration', module='progress',
                   state=dict(label='Water', unit='oz', value=16, goal=64, step=8))
    elif any(word in lower for word in ('score', 'ping pong')):
        app = dict(id='score', title='scoreboard', module='scoreboard',
                   state={'cursor': 0, 'sides': [{'name': 'Me', 'score': 0}, {'name': 'Alex', 'score': 0}]})
    elif any(word in lower for word in ('timer', 'focus', 'pomodoro')):
        app = dict(id='focus', title='pomodoro', module='progress',
                   state=dict(label='Focus', unit='min', value=0, goal=100, step=25))
    else:
        title = text
        for prefix in ('create ', 'make ', 'build '):
            if title.lower().startswith(prefix): title = title[len(prefix):]
        app = dict(id='custom', title=title[:32] or 'new app', module='checklist',
                   state={'cursor': 0, 'items': [{'label': 'First item', 'checked': False}]})
    base = app['id']; suffix = 2
    while any(existing['id'] == app['id'] for existing in registry):
        app['id'] = f'{base}_{suffix}'; suffix += 1
    return app


class PartialSpeechDemo:
    """Timed Vosk-shaped hypotheses for the microphone-free speech demo."""
    def __init__(self, text):
        self.text = text
        words = text.lower().split()
        words = [word.strip('.,!?;:') for word in words]
        words = [word for word in words if word]
        self.events = [(0, '')]
        at = 250
        for index, word in enumerate(words):
            prefix = words[:index]
            if word == 'milk':
                # A provisional hypothesis is replaced as more audio arrives.
                self.events.append((at, ' '.join(prefix + ['mill'])))
                at += 320
            self.events.append((at, ' '.join(prefix + [word])))
            at += 300 + min(len(word), 8)*25

    def partial_result(self, elapsed):
        hypothesis = ''
        for at, text in self.events:
            if at > elapsed:
                break
            hypothesis = text
        return {'partial': hypothesis}

    def final_result(self):
        return {'text': self.text}


class NativeScreen(legacy.Screen):
    def __init__(self, prefs):
        super().__init__()
        self.prefs = prefs
        self.position = self.target = 0.0
        self.wheel_start = None
        self.last_view = None
        self.transition = None
        self.transition_value = 0.0
        self.keyboard = None
        self.keyboard_shift = False
        self.setting_cursor = 0
        self.calculator = ''
        self.listening_text = ''
        self.submitted_text = ''
        self.transcript = TranscriptAnimator()
        self.wave = []
        self.arrows = []
        self.time = 0
        self.theme = None

    def palette(self):
        theme = self.prefs['theme']
        if theme != self.theme:
            self.theme = theme
            legacy.BG = (0, 0, 0) if theme == 'dark' else (255, 255, 255)
            legacy.INK = (255, 255, 255) if theme == 'dark' else (0, 0, 0)
            legacy.MUTED = (156, 156, 156) if theme == 'dark' else (85, 85, 85)
            legacy.CARD = legacy.CARD2 = legacy.CURSOR = (30, 30, 30) if theme == 'dark' else (235, 235, 235)
            legacy.ACCENT = legacy.GREEN = legacy.INK
            legacy.ACCENT_INK = legacy.BG
            legacy._marks.clear()
        self.bg, self.ink = legacy.BG, legacy.INK

    def label(self, surf, text, pos, size=20, word=False, align='center', width=440, color=None):
        font = self.font(round(size*self.prefs['text_scale']), word=word)
        rendered = self.text(font, text, width, color or self.ink)
        rect = rendered.get_rect()
        setattr(rect, {'center': 'center', 'left': 'midleft', 'right': 'midright'}[align], pos)
        surf.blit(rendered, rect)
        return rect

    def button(self, surf, rect, caption, act, **kwargs):
        rect = pygame.Rect(rect)
        pygame.draw.rect(surf, self.ink, rect, 1, border_radius=12)
        if caption == '⌫':
            x,y=rect.center
            pygame.draw.polygon(surf,self.ink,[(x-15,y),(x-7,y-10),(x+14,y-10),(x+14,y+10),(x-7,y+10)],2)
            pygame.draw.line(surf,self.ink,(x-2,y-4),(x+6,y+4),2)
            pygame.draw.line(surf,self.ink,(x-2,y+4),(x+6,y-4),2)
        elif caption == '↵':
            x,y=rect.center
            pygame.draw.lines(surf,self.ink,False,[(x+12,y-9),(x+12,y+3),(x-12,y+3),(x-5,y-4)],2)
            pygame.draw.line(surf,self.ink,(x-12,y+3),(x-5,y+10),2)
        else:self.label(surf, caption, rect.center, 22, width=rect.width-12)
        self.add(rect, act, **kwargs)

    def tween(self, states, bases, spread, now):
        if not states:
            states.extend(dict(start=now, duration=random.uniform(350, 950), old=base,
                               target=base+random.uniform(-spread, spread)) for base in bases)
        result = []
        for state, base in zip(states, bases):
            t = min(1, max(0, (now-state['start'])/state['duration']))
            t = t*t*(3-2*t)
            value = state['old']+(state['target']-state['old'])*t
            result.append(value)
            if t >= 1:
                state.update(start=now, duration=random.uniform(200, 800), old=value,
                             target=base+random.uniform(-spread, spread))
        return result

    def logo(self, surf, center, size, waiting=False):
        # A separate alpha layer preserves the black/white center of the mark.
        size = max(1, round(size)); pad = round(size*.15)
        layer = pygame.Surface(((size+pad*2)*2, (size+pad*2)*2), pygame.SRCALPHA)
        scale = size*2/140
        inset = pad*2
        offsets = self.tween(self.arrows, [0]*5, 12, self.time) if waiting and self.prefs['motion'] else [0]*5
        for arrow, offset in zip(legacy.ARROWS, offsets):
            angle, length, hl, hw, sw = arrow
            points = legacy.arrow_points(angle, length+offset, hl, hw, sw)
            pygame.draw.polygon(layer, self.ink, [(x*scale+inset, y*scale+inset) for x,y in points])
        c = (size+inset, size+inset)
        pygame.draw.circle(layer, self.ink, c, 22*scale)
        pygame.draw.circle(layer, (0,0,0,0), c, 11*scale)
        layer = pygame.transform.smoothscale(layer, (size+pad*2, size+pad*2))
        surf.blit(layer, layer.get_rect(center=center))

    def voice(self, surf, listening):
        heights = self.tween(self.wave, [18,30,36,26,20], 16, self.time) if listening and self.prefs['motion'] else [12,24,40,28,16]
        for i,h in enumerate(heights):
            pygame.draw.rect(surf, self.ink, (208+i*14, 664-h/2, 8, h))
        self.add(VOICE, 'talk')

    def wheel_to(self, target):
        self.target = float(target)
        self.selection = round(target)
        if not self.prefs['motion']:
            self.position = self.target; self.wheel_start = None
        else:
            self.wheel_start = (self.time, self.position)

    def step_selection(self, device, direction):
        self.launcher = True
        self.wheel_to(round(self.target)+direction)

    def update_wheel(self):
        if self.wheel_start:
            start, old = self.wheel_start
            t = min(1, max(0, (self.time-start)/280))
            self.position = old+(self.target-old)*(1-(1-t)**3)
            if t >= 1: self.wheel_start = None
        self.selection = round(self.position)

    def arc(self, surf, device, brand=True, heading=True):
        if brand:
            self.logo(surf, (410,112),94)
            self.label(surf,'omni',(350,106),36,True,'right')
            self.add((270,65,195,90),'logo')
        if not device.registry: return
        n = len(device.registry)
        selected = device.registry[self.selection % n]
        if heading:
            self.label(surf, selected['title'].lower(),(444,211),32,True,'right',410)
            pygame.draw.rect(surf,self.ink,(374,249,70,4))
        pygame.draw.circle(surf,self.ink,(CX,CY),RADIUS,2)
        nodes=[]; seen=set(); center=round(self.position)
        for slot in sorted(range(center-5,center+6),key=lambda slot:abs(slot-self.position)):
            distance=slot-self.position;angle=FOCUS+distance*STEP;index=slot%n
            if not math.radians(-108)<=angle<=math.radians(40) or index in seen: continue
            seen.add(index);nodes.append((slot,index,distance,angle))
        for slot,index,distance,angle in reversed(nodes):
            focus=max(0,1-abs(distance));focus=focus*focus*(3-2*focus)
            radius=28+30*focus
            x=CX+math.cos(angle)*RADIUS;y=CY+math.sin(angle)*RADIUS
            fill=tuple(round(a+(b-a)*focus) for a,b in zip(self.bg,self.ink))
            color=tuple(round(a+(b-a)*focus) for a,b in zip(self.ink,self.bg))
            pygame.draw.circle(surf,fill,(x,y),radius)
            pygame.draw.circle(surf,self.ink,(x,y),radius,2)
            self.icon(surf,device.registry[index],(x,y),radius,color)
            self.add((x-radius,y-radius,2*radius,2*radius),
                     'open' if index==self.selection%n and abs(distance)<.02 else 'select',
                     index=slot,app_id=device.registry[index]['id'])

    def icon(self,surf,app,center,radius,color):
        x,y=center;s=radius*.47;module=app['module'];w=max(2,round(radius/15))
        if module=='home':
            layer=pygame.Surface((100,100),pygame.SRCALPHA)
            # Draw directly with requested inverted color for selected nodes.
            for arrow in legacy.ARROWS:
                pygame.draw.polygon(layer,color,[(a*.55+11,b*.55+11) for a,b in legacy.arrow_points(*arrow)])
            pygame.draw.circle(layer,color,(50,50),12);pygame.draw.circle(layer,(0,0,0,0),(50,50),6)
            layer=pygame.transform.smoothscale(layer,(round(radius*1.3),round(radius*1.3)))
            surf.blit(layer,layer.get_rect(center=center))
        elif module=='settings':
            pygame.draw.circle(surf,color,center,s*.7,w);pygame.draw.circle(surf,color,center,s*.25,w)
            for i in range(8):
                a=i*math.tau/8
                pygame.draw.line(surf,color,(x+math.cos(a)*s*.65,y+math.sin(a)*s*.65),
                                 (x+math.cos(a)*s,y+math.sin(a)*s),w+1)
        elif module=='clock':
            pygame.draw.circle(surf,color,center,s,w)
            pygame.draw.lines(surf,color,False,[(x,y-s*.6),(x,y),(x+s*.5,y)],w)
        elif module in ('notes','calculator'):
            pygame.draw.rect(surf,color,(x-s*.8,y-s*1.1,s*1.6,s*2.2),w)
            if module=='notes':
                for row in (-1,0,1):pygame.draw.line(surf,color,(x-s*.5,y+row*s*.55),(x+s*.5,y+row*s*.55),w)
            else:
                pygame.draw.rect(surf,color,(x-s*.5,y-s*.8,s,s*.4),w)
                for row in range(3):
                    for col in range(2):pygame.draw.rect(surf,color,(x-s*.5+col*s*.65,y+row*s*.4,s*.35,s*.22))
        else:self.app_icon(surf,app,center,radius,color)

    def transition_progress(self, view):
        if view != self.last_view:
            old=self.last_view;self.last_view=view
            if old in ('home','arc') and view in ('home','arc') and self.prefs['motion']:
                start=self.transition_value if self.transition else (1 if old=='arc' else 0)
                self.transition=(self.time,start,1 if view=='arc' else 0)
            else:self.transition=None
        if self.transition:
            start,old,target=self.transition;t=min(1,max(0,(self.time-start)/480))
            eased=t*t*t*(t*(t*6-15)+10)
            self.transition_value=old+(target-old)*eased
            if t>=1:self.transition=None
        return self.transition_value

    def paint(self,surf,device,ticks,draft):
        self.time=ticks;self.palette();self.update_wheel();self.hits.clear()
        surf.fill(self.bg);self.content_h=0
        app=device.current();view='app' if app else 'arc' if self.launcher else 'home'
        p=self.transition_progress(view)
        if self.transition:
            layer=pygame.Surface((480,800),pygame.SRCALPHA)
            self.arc(layer,device,False,False)
            layer.set_alpha(round(255*p));surf.blit(layer,(-64*(1-p),100*(1-p)))
            self.logo(surf,(240+170*p,320-208*p),246-152*p)
            face=self.font(round(36*self.prefs['text_scale']),word=True)
            end=350-face.size('omni')[0]/2
            self.label(surf,'omni',(240+(end-240)*p,490-384*p),64-28*p,True)
            if p>.82 and device.registry:
                layer=pygame.Surface((480,800),pygame.SRCALPHA)
                self.label(layer,device.registry[self.selection%len(device.registry)]['title'].lower(),(444,211),32,True,'right',410)
                pygame.draw.rect(layer,self.ink,(374,249,70,4));layer.set_alpha(round((p-.82)/.18*255));surf.blit(layer,(0,0))
            self.hits.clear()
        elif view=='home':
            self.logo(surf,(240,320),246,device.agent=='thinking')
            self.label(surf,'omni',(240,490),64,True)
            self.add((0,58,480,560),'launcher')
            self.voice(surf,device.agent=='listening')
            if device.say and device.agent != 'listening':self.label(surf,device.say,(240,566),17,width=420)
            else:self.input_visual(surf,device,draft)
            self.add((390,730,66,48),'request')
            pygame.draw.rect(surf,self.ink,(402,742,42,25),1,border_radius=3)
            for row in range(2):
                for col in range(5):pygame.draw.rect(surf,self.ink,(407+col*7,747+row*6,3,3))
            pygame.draw.line(surf,self.ink,(413,762),(433,762),2)
        elif view=='arc':self.arc(surf,device)
        elif app['module'] in ('settings','notes','clock','calculator'):
            self.utility(surf,device,app)
        else:
            body=pygame.Rect(0,58,480,726);surf.set_clip(body)
            self.app_view(surf,device,app,body);surf.set_clip(None)
        if self.keyboard:self.draw_keyboard(surf,device)

    def input_visual(self, surf, device, draft):
        if not self.prefs['show_input']:
            self.transcript.clear()
            return
        if device.agent == 'listening':text=self.listening_text
        elif device.agent == 'thinking':text=self.submitted_text
        else:text=draft or self.submitted_text
        font=self.font(round(22*self.prefs['text_scale']))
        line_height=round(28*self.prefs['text_scale'])
        self.transcript.update(text,self.time,lambda value:font.size(value)[0],
                               line_height=line_height,animate=self.prefs['motion'],align='center')
        if not text:return
        # Each line remains centered; position changes ease as the text grows.
        # Recognition/submission always use the original, unanimated text.
        layer=pygame.Surface((408,66),pygame.SRCALPHA)
        for word,x,y,opacity in self.transcript.frames(self.time):
            if opacity<=0 or y < -line_height or y>=66:continue
            glyph=font.render(word,True,self.ink)
            glyph.set_alpha(round(255*opacity))
            layer.blit(glyph,(round(x),round(y)+4))
        if self.transcript.scroll(self.time)>1:
            mask=pygame.Surface(layer.get_size(),pygame.SRCALPHA)
            mask.fill((255,255,255,255))
            for row in range(8):
                pygame.draw.line(mask,(255,255,255,round(row/7*255)),(0,row),(408,row))
            layer.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(layer,(36,556))

    def utility(self,surf,device,app):
        self.label(surf,app['title'],(40,100),32,True,'left',330)
        self.button(surf,(388,70,56,56),'‹','back')
        module=app['module']
        if module=='settings':
            prefs=self.prefs
            rows=[('Appearance','Dark' if prefs['theme']=='dark' else 'Light'),
                  ('Motion','On' if prefs['motion'] else 'Reduced'),
                  ('Text size','Standard' if prefs['text_scale']==1 else 'Large'),
                  ('Preview wait',f"{prefs['wait_seconds']} seconds"),
                  ('Live input','Shown' if prefs['show_input'] else 'Hidden'),('Back to apps','‹')]
            for index,(label,value) in enumerate(rows):
                rect=pygame.Rect(24,180+index*88,432,72)
                pygame.draw.rect(surf,self.ink,rect,2 if index==self.setting_cursor else 1,border_radius=12)
                self.label(surf,label,(42,rect.y+23),18,align='left',width=380)
                self.label(surf,value,(438,rect.y+50),20,align='right',width=380)
                self.add(rect,'setting',index=index)
        elif module=='notes':
            text=app['state'].get('text','')
            lines=[]
            for paragraph in (text or 'Tap to write a note…').split('\n'):
                line=''
                for word in paragraph.split(' '):
                    if self.font(20).size(line+' '+word)[0]>396:
                        lines.append(line);line=word
                    else:line=(line+' '+word).strip()
                lines.append(line)
            area=pygame.Rect(24,160,432,560);surf.set_clip(area)
            for i,line in enumerate(lines):self.label(surf,line,(42,184+i*32-self.scroll),20,align='left',width=396)
            surf.set_clip(None);self.content_h=max(726,len(lines)*32+160)
            self.add(area,'edit_notes')
        elif module=='clock':
            now=datetime.datetime.now();pattern='%H:%M' if self.prefs['clock24'] else '%I:%M %p'
            self.label(surf,now.strftime(pattern),(240,335),58,True,width=440)
            self.label(surf,now.strftime('%A, %B %d'),(240,425),20)
            self.label(surf,time.tzname[time.localtime().tm_isdst],(240,468),16)
            self.button(surf,(140,580,200,58),'24-hour' if self.prefs['clock24'] else '12-hour','clock_format')
        else:
            self.label(surf,self.calculator or '0',(438,200),38,True,'right',400)
            rows=[['C','±','⌫','÷'],['7','8','9','×'],['4','5','6','−'],['1','2','3','+'],['0','.','=']]
            for row,keys in enumerate(rows):
                for col,key in enumerate(keys):
                    self.button(surf,(24+col*110,280+row*88,212 if key=='=' else 102,76),key,'calc',text=key)

    def draw_keyboard(self,surf,device):
        pygame.draw.rect(surf,self.bg,(0,365,480,435))
        pygame.draw.line(surf,self.ink,(0,365),(480,365))
        text=self.keyboard['text']
        self.label(surf,text[-44:] or ('Write a note' if self.keyboard['kind']=='notes' else 'Describe an app'),(24,397),18,align='left',width=432)
        for row,keys in enumerate(('1234567890','qwertyuiop','asdfghjkl','zxcvbnm')):
            width=44;left=(480-len(keys)*width)/2
            for col,key in enumerate(keys):
                self.button(surf,(left+col*width,430+row*62,width-4,54),key.upper() if self.keyboard_shift else key,'key',text=key.upper() if self.keyboard_shift else key)
        self.button(surf,(12,616,64,54),'Aa','key',text='shift')
        self.button(surf,(404,616,64,54),'.','key',text='.')
        for x,w,label,key in [(12,90,'⌫','backspace'),(108,90,'↵','newline'),(204,150,'space',' '),(360,108,'Done','done')]:
            self.button(surf,(x,690,w,60),label,'key',text=key)
        # Every input is captured by the keyboard while it is open.
        self.hits=[hit for hit in self.hits if hit.act=='key']


class NativeApp(legacy.App):
    def __init__(self, stub, turn, kiosk, store=None, live=False, speech=None, backend=None):
        # Separate from the retired demo registry; existing device data is intact.
        store=Path(store) if store else Path.home()/'.omni'/'pi-ui'/'registry.json'
        self.store=store;self.preferences_path=store.with_name('preferences.json')
        self.prefs=DEFAULTS.copy()
        try:
            saved=json.loads(self.preferences_path.read_text())
            for key,choices in dict(theme=('dark','light'),motion=(True,False),text_scale=(1,1.15),wait_seconds=(3,10,20),clock24=(True,False),show_input=(True,False)).items():
                if saved.get(key) in choices:self.prefs[key]=saved[key]
        except (OSError,ValueError,TypeError):pass
        self.device=Device();self.device.load_modules()
        if not self.device.restore(store):self.device.registry=default_apps()
        # Built-ins are always present, in the same order on the simulator/Pi.
        existing={app.get('id'):app for app in self.device.registry if isinstance(app,dict)}
        builtins=default_apps()
        for app in builtins:
            old=existing.get(app['id'])
            if old and old.get('module')==app['module'] and isinstance(old.get('state'),dict):app['state']=old['state']
        builtin_ids={app['id'] for app in builtins}
        self.device.registry=builtins+[app for app in self.device.registry if isinstance(app,dict) and app.get('id') not in builtin_ids and isinstance(app.get('state'),dict)]
        self.device.go_home();self.device.save(store)
        self.screen=NativeScreen(self.prefs)
        self.stub=stub;self.turn=turn if kiosk else 'none';self.kiosk=kiosk
        self.backend=backend or ('stub' if live else 'demo');self.live=self.backend!='demo'
        self.recorder=legacy.AudioRecorder()
        self.draft='';self.events=legacy.queue.Queue();self.press=None;self.stopping=False
        self.phone=pygame.Surface((480,800))
        self.pending=None;self.request_number=0
        self.speech_preview=None;self.speech_segments=[]
        self.speech=speech;self.speech_session=None;self.speech_finalizing=False

    def save_preferences(self):
        self.preferences_path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.preferences_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.prefs,indent=2));temporary.replace(self.preferences_path)

    def set_launcher(self, value):
        self.device.go_home();self.screen.launcher=value;self.screen.scroll=0
        self.device.save(self.store)

    def send(self,text="",wav_base64=None):
        text=(text or '').strip()
        if (not text and not wav_base64) or self.pending:return
        self.screen.submitted_text=text
        self.draft='';self.screen.keyboard=None;self.screen.wave.clear();self.screen.arrows.clear()
        self.set_launcher(False)
        self.device.agent='thinking';self.device.say='';self.device.respond_until=None
        self.request_number+=1
        due=time.monotonic()+self.prefs['wait_seconds']
        self.pending=dict(request=text or 'Voice request',due=due,number=self.request_number)
        if self.live:
            payload=dict(text=text,registry=copy.deepcopy([a for a in self.device.registry if a['module'] not in {b[2] for b in BUILTINS}]),focused_app_id=None)
            if wav_base64:
                payload['wav_base64']=wav_base64
            import threading
            threading.Thread(target=self.fetch_native,args=(payload,self.request_number),daemon=True).start()

    def fetch_native(self,payload,number):
        if self.backend=='gemini':
            root=str(Path(__file__).resolve().parents[1])
            if root not in sys.path:sys.path.insert(0,root)
            from cloud.try_turn import TurnError, ask
            print('Speech: %s' % payload['text'],flush=True)
            try:
                result=ask(payload['text'],payload['registry'],wav_base64=payload.get('wav_base64'))
                print('Gemini turn:\n%s' % json.dumps(result,indent=2),flush=True)
            except TurnError as error:
                print('Gemini: %s' % error,flush=True)
                result={'op':'say','say':str(error)}
            self.events.put((number,result))
            return
        try:self.events.put((number,legacy.post_json(self.stub,payload)))
        except (OSError,ValueError):self.events.put((number,None))

    def select_app(self,app):
        base=app['id'];suffix=2
        while self.device.find(app['id']):app['id']=f'{base}_{suffix}';suffix+=1
        self.device.registry.append(app)
        index=len(self.device.registry)-1
        self.screen.selection=index;self.screen.position=self.screen.target=float(index);self.screen.wheel_start=None
        self.device.agent='idle';self.device.say='';self.set_launcher(True)

    def poll(self):
        self.poll_speech()
        if not self.pending:return
        while not self.events.empty():
            number,result=self.events.get_nowait()
            if number==self.pending['number']:self.pending['result']=result
        if time.monotonic()<self.pending['due']:return
        if self.live and 'result' not in self.pending:return
        pending=self.pending;self.pending=None
        if not self.live:
            self.select_app(demo_app(pending['request'],self.device.registry));return
        result=pending['result']
        if result and result.get('op')=='propose' and isinstance(result.get('app'),dict):
            app=result['app']
            if app.get('id') and app.get('module') in self.device.modules and isinstance(app.get('state'),dict):
                self.select_app(copy.deepcopy(app));return
        if result and result.get('op')=='mutate':
            self.device.apply_turn(result,time.monotonic())
            app=self.device.current()
            if app:
                index=self.device.registry.index(app)
                self.screen.position=self.screen.target=float(index);self.screen.selection=index
                self.device.agent='idle';self.set_launcher(True);return
        self.device.agent='idle'
        self.device.say=(result or {}).get('say') or 'Could not reach the turn server. Try again.'

    def change_setting(self,index):
        self.screen.setting_cursor=index
        if index==0:self.prefs['theme']='light' if self.prefs['theme']=='dark' else 'dark'
        elif index==1:
            self.prefs['motion']=not self.prefs['motion']
            if not self.prefs['motion']:
                self.screen.transition=None;self.screen.position=self.screen.target;self.screen.wheel_start=None
        elif index==2:self.prefs['text_scale']=1.15 if self.prefs['text_scale']==1 else 1
        elif index==3:
            values=[3,10,20];self.prefs['wait_seconds']=values[(values.index(self.prefs['wait_seconds'])+1)%3]
        elif index==4:self.prefs['show_input']=not self.prefs['show_input']
        else:self.set_launcher(True)
        self.save_preferences()

    def calculator_key(self,key):
        value=self.screen.calculator
        if key=='C':value=''
        elif key=='⌫':value=value[:-1]
        elif key=='=':
            try:value=calculate(value)
            except (ValueError,SyntaxError,ZeroDivisionError,OverflowError):value='Error'
        elif key=='±':
            try:value=calculate(f'-({value})')
            except (ValueError,SyntaxError,ZeroDivisionError,OverflowError):value='Error'
        else:
            if value=='Error':value=''
            if len(value)<40:value+=dict(zip(('×','÷','−'),('*','/','-'))).get(key,key)
        self.screen.calculator=value

    def keyboard_key(self,key):
        keyboard=self.screen.keyboard
        if not keyboard:return
        if key=='shift':self.screen.keyboard_shift=not self.screen.keyboard_shift;return
        if key=='done':
            if keyboard['kind']=='request':self.draft=keyboard['text']
            self.screen.keyboard=None;return
        if key=='backspace':keyboard['text']=keyboard['text'][:-1]
        else:keyboard['text']+= '\n' if key=='newline' else key
        if keyboard['kind']=='notes':
            self.device.find('notes')['state']['text']=keyboard['text'];self.device.save(self.store)
        else:self.draft=keyboard['text']

    def activate(self,hit):
        if hit is None or self.pending or self.screen.transition:return
        act=hit.act
        if act=='launcher':self.set_launcher(True);return
        if act=='logo':self.set_launcher(False);return
        if act=='select':self.screen.wheel_to(hit.index);return
        if act=='open' and hit.app_id=='omni':self.set_launcher(False);return
        if act=='back':self.set_launcher(True);return
        if act=='setting':self.change_setting(hit.index);return
        if act=='clock_format':self.prefs['clock24']=not self.prefs['clock24'];self.save_preferences();return
        if act=='calc':self.calculator_key(hit.text);return
        if act=='edit_notes':
            self.screen.keyboard=dict(kind='notes',text=self.device.find('notes')['state'].get('text',''));return
        if act=='request':self.screen.keyboard=dict(kind='request',text=self.draft);return
        if act=='key':self.keyboard_key(hit.text);return
        super().activate(hit)

    def on_down(self,pos):
        if pos is None or self.pending or self.speech_session is not None or self.screen.transition:return
        hit=self.screen.at(pos)
        now=pygame.time.get_ticks();self.screen.time=now
        self.press=dict(x=pos[0],y=pos[1],hit=hit,time=now,talk=bool(hit and hit.act=='talk'),moved=False,
                        scroll=self.screen.scroll)
        if self.press['talk']:
            self.device.say=''
            self.screen.submitted_text=''
            self.screen.listening_text=''
            self.screen.transcript.clear()
            self.speech_segments=[]
            self.device.agent='listening';self.screen.wave.clear()
            if self.speech:
                try:self.speech_session=self.speech.start()
                except Exception as error:
                    self.device.agent='idle';self.device.say=str(error);self.press=None
            else:
                self.recorder.start()
                self.speech_preview=PartialSpeechDemo(self.draft or legacy.TALK_LINE)
        elif self.screen.launcher and not self.device.current() and pos[1]>295:
            self.screen.wheel_start=None;self.screen.target=self.screen.position
            self.press.update(wheel=True,angle=math.atan2(pos[1]-CY,pos[0]-CX))

    def on_move(self,pos):
        press=self.press
        if not press or pos is None or press['talk'] or self.screen.keyboard:return
        if not press['moved'] and math.hypot(pos[0]-press['x'],pos[1]-press['y'])<6:return
        press['moved']=True
        if press.get('wheel'):
            angle=math.atan2(pos[1]-CY,pos[0]-CX)
            delta=math.atan2(math.sin(angle-press['angle']),math.cos(angle-press['angle']))
            press['angle']=angle
            self.screen.position-=delta/STEP;self.screen.target=self.screen.position
            self.screen.selection=round(self.screen.position)
        elif self.device.current():self.screen.scroll=max(0,press['scroll']-(pos[1]-press['y']))

    def cancel_press(self):
        if self.press and self.press.get('wheel'):self.screen.wheel_to(round(self.screen.position))
        self.press=None
        if self.speech_session is not None:
            self.speech.cancel(self.speech_session)
            self.speech_session=None;self.speech_finalizing=False
            if not self.pending:self.device.agent='idle'
        if self.device.agent=='listening':self.device.agent='idle'
        self.speech_preview=None;self.speech_segments=[];self.screen.listening_text=''
        self.screen.wave.clear()
        self.recorder.stop()

    def on_up(self,pos):
        press=self.press;self.press=None
        if not press:return
        if press['talk']:
            should_send=pos is not None and pygame.time.get_ticks()-press['time']>=350
            if self.speech and self.speech_session is not None:
                if should_send:
                    self.speech_finalizing=True
                    self.screen.submitted_text=self.screen.listening_text
                    self.screen.arrows.clear()
                    self.device.agent='thinking';self.screen.wave.clear()
                    self.speech.finish(self.speech_session)
                else:self.cancel_press()
                return
            if should_send and self.speech_preview:
                self.apply_speech_result(self.speech_preview.final_result())
            transcript=self.screen.listening_text
            self.device.agent='idle';self.screen.wave.clear()
            wav_b64=self.recorder.stop()
            self.speech_preview=None;self.speech_segments=[]
            if should_send:
                fallback=transcript or (self.draft or (legacy.TALK_LINE if not wav_b64 else ''))
                self.send(fallback,wav_base64=wav_b64)
            else:self.screen.listening_text=''
            return
        if press.get('wheel') and press['moved']:
            self.screen.wheel_to(round(self.screen.position));return
        if not press['moved'] and pos is not None:
            hit=self.screen.at(pos)
            if hit and press['hit'] and hit.act==press['hit'].act:self.activate(hit)

    def scroll_input(self,direction):
        if self.pending or self.speech_session is not None or self.screen.transition or self.screen.keyboard:return
        app=self.device.current()
        if app and app['module']=='settings':self.screen.setting_cursor=(self.screen.setting_cursor+direction)%SETTINGS_COUNT
        elif app:self.screen.scroll=max(0,self.screen.scroll+direction*48)
        else:self.screen.step_selection(self.device,direction)

    def on_key(self,event):
        mods=event.mod;ctrl=bool(mods & (pygame.KMOD_CTRL|pygame.KMOD_META))
        if ctrl and event.key==pygame.K_q and mods & pygame.KMOD_SHIFT:return 'quit'
        if event.key==pygame.K_ESCAPE:
            if self.speech_session is not None:self.cancel_press()
            elif self.screen.keyboard:self.screen.keyboard=None
            elif self.pending:
                self.request_number+=1;self.pending=None;self.device.agent='idle';self.device.say=''
            elif self.device.current():self.set_launcher(True)
            elif self.screen.launcher:self.set_launcher(False)
            return
        if self.pending or self.speech_session is not None or self.screen.transition:return
        if ctrl and event.key==pygame.K_d:
            self.device.registry=default_apps();self.device.save(self.store);self.screen.position=self.screen.target=0;self.set_launcher(True);return
        if ctrl:return
        if self.screen.keyboard:
            if event.key==pygame.K_BACKSPACE:self.keyboard_key('backspace')
            elif event.key==pygame.K_RETURN:self.keyboard_key('newline' if self.screen.keyboard['kind']=='notes' else 'done')
            return
        app=self.device.current()
        if app and app['module']=='calculator':
            key={pygame.K_RETURN:'=',pygame.K_BACKSPACE:'⌫',pygame.K_DELETE:'C'}.get(event.key)
            if key:self.calculator_key(key)
            return
        if app and app['module']=='notes':
            if event.key==pygame.K_BACKSPACE:
                app['state']['text']=app['state'].get('text','')[:-1];self.device.save(self.store)
            elif event.key==pygame.K_RETURN:
                app['state']['text']=app['state'].get('text','')+'\n';self.device.save(self.store)
            return
        if event.key in (pygame.K_UP,pygame.K_DOWN):self.scroll_input(-1 if event.key==pygame.K_UP else 1);return
        if event.key==pygame.K_RETURN:
            if app and app['module']=='settings':self.change_setting(self.screen.setting_cursor)
            elif not app and self.draft:self.send(self.draft)
            elif not app and not self.screen.launcher:self.set_launcher(True)
            elif not app:
                index=round(self.screen.target)%len(self.device.registry)
                self.activate(legacy.Hit((0,0,1,1),'open',app_id=self.device.registry[index]['id']))
        elif event.key==pygame.K_BACKSPACE:
            self.draft=self.draft[:-1]
            if self.device.agent=='listening':
                self.speech_preview=None
                self.screen.listening_text=self.draft

    def on_text(self,text):
        if self.pending or self.speech_session is not None or self.screen.transition or not text:return
        if self.screen.keyboard:self.keyboard_key(text);return
        app=self.device.current()
        if app and app['module']=='notes':
            app['state']['text']=app['state'].get('text','')+text;self.device.save(self.store)
        elif app and app['module']=='calculator':
            for key in text:
                if key in '0123456789.+-*/=':self.calculator_key(key)
        elif app is None:
            self.draft+=text
            if self.device.agent=='listening':
                self.speech_preview=None
                self.screen.listening_text=self.draft

    def poll_speech(self):
        if not self.speech:return
        for number,kind,payload in self.speech.poll():
            if number != self.speech_session:continue
            if kind in ('partial','segment'):
                self.apply_speech_result(payload)
            elif kind=='ready':
                print(f"Microphone ready: {payload['device']} ({payload['samplerate']} Hz)", flush=True)
            elif kind=='warning':
                print(f'Microphone warning (continuing): {payload}',flush=True)
            elif kind=='final' and self.speech_finalizing:
                text=payload.get('text','').strip()
                self.speech_session=None;self.speech_finalizing=False
                self.speech_segments=[];self.screen.listening_text=text
                self.screen.submitted_text=text
                self.device.agent='idle'
                if text:
                    print(f'Recognized: {text}',flush=True)
                    self.send(text)
                else:
                    self.screen.submitted_text=''
                    self.device.say='No speech detected. Hold the waveform and try again.'
            elif kind=='error':
                print(f'Microphone error: {payload}',flush=True)
                self.cancel_press()
                self.device.agent='idle';self.device.say='Microphone error. Check your input device.'
                self.screen.submitted_text=''

    def close(self):
        self.cancel_press()
        if self.speech:self.speech.close()

    def apply_speech_result(self, result):
        """Replace partial hypotheses; retain finalized segments across pauses.

        A real Vosk worker can deliver PartialResult/Result JSON through this
        same method on the UI thread. Late results after release are ignored.
        """
        if self.device.agent != 'listening':
            return
        if 'text' in result:
            text=str(result['text']).strip()
            if text:self.speech_segments.append(text)
            partial=''
        elif 'partial' in result:
            partial=str(result['partial']).strip()
        else:
            return
        self.screen.listening_text=' '.join(self.speech_segments+([partial] if partial else []))

    def update_speech_preview(self, ticks):
        if self.press and self.press['talk'] and self.speech_preview:
            result=self.speech_preview.partial_result(ticks-self.press['time'])
            self.apply_speech_result(result)

    def frame(self,display):
        ticks=pygame.time.get_ticks()
        self.screen.time=ticks
        self.update_speech_preview(ticks)
        super().frame(display)
