"""Shared desktop/Pi UI. The simulator and kiosk use the same input and paint path."""
from __future__ import annotations

import copy
import datetime
import json
import math
import random
import sys
import time
from pathlib import Path

import pygame
import phone as legacy
from logic import Device
from local_commands import calculate, theme_command, match_command
from transcript import TranscriptAnimator,short_response
from contract.runtime import ContractError, validate_app, validate_turn, apply_operations, fields, message, preview_navigation
from contract.legacy import to_composed
from speaker import speak
from contract.asset_catalog import app_icon as app_asset,component_icon
from icon_assets import draw as draw_asset

BUILTINS = (
    ('omni', 'omni', 'home'), ('settings', 'settings', 'settings'),
    ('notes', 'notes', 'notes'), ('clock', 'clock', 'clock'),
    ('calculator', 'calculator', 'calculator'),
)
DEFAULTS = dict(theme='dark', motion=True, text_scale=1.15, wait_seconds=10, clock24=True)
SETTINGS_COUNT = 3
CX, CY, RADIUS, STEP, FOCUS = -8, 686, 328, math.radians(22), math.radians(-42)
VOICE = pygame.Rect(192, 626, 96, 76)
TOUCH_SLOP = 14
TOUCH_PADDING = 12
LINE_W = 2


def default_apps():
    return [dict(id=id, title=title, module=module, state={'text': ''} if module == 'notes' else {})
            for id, title, module in BUILTINS]



def demo_app(request, registry):
    """Local stand-in for a model response, shared by simulator and kiosk."""
    text = request.strip()
    lower = text.lower()
    if 'rock paper scissors' in lower.replace('-',' ') or 'rps' in lower.split():
        app=json.loads((legacy.ROOT/'contract/fixtures/v2/rock-paper-scissors.json').read_text())
    elif any(word in lower for word in ('expense','budget','spending')):
        app=json.loads((legacy.ROOT/'contract/fixtures/v2/expense-log.json').read_text())
    elif 'counter' in lower:
        app=json.loads((legacy.ROOT/'contract/fixtures/v2/counter.json').read_text())
    elif any(word in lower for word in ('milk', 'shop', 'grocer')):
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
        for prefix in ('create a ', 'create an ', 'create ', 'make a ', 'make an ', 'make ', 'build a ', 'build an ', 'build ', 'new '):
            if title.lower().startswith(prefix): title = title[len(prefix):]
        short_words = []
        for w in title.split():
            cand = ' '.join(short_words + [w])
            if len(cand) <= 16: short_words.append(w)
            else: break
        title = ' '.join(short_words) or title[:16].strip()
        app = dict(id='custom', title=title or 'new app', module='checklist',
                   state={'cursor': 0, 'items': [{'label': 'First item', 'checked': False}]})
    base = app['id']; suffix = 2
    while any(existing['id'] == app['id'] for existing in registry):
        app['id'] = f'{base}_{suffix}'; suffix += 1
    return to_composed(app)


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
        self.page_transition = None
        self.navigation = None
        self.wheel_duration = 280
        self.keyboard = None
        self.keyboard_shift = False
        self.setting_cursor = 0
        self.delete_apps_confirm = False
        self.calculator = ''
        self.app_notice = ''
        self.removed_item = None
        self.notice_until = None
        self.app_pages = {}
        self.page_scroll = {}
        self.slider_preview = None
        self.scroll_limit = 0
        self.app_body = pygame.Rect(0,144,480,640)
        self.listening_text = ''
        self.submitted_text = ''
        self.transcript = TranscriptAnimator()
        self.text_mode = None
        self.response_source = None
        self.response_target = ''
        self.response_started = 0
        self.wave = []
        self.arrows = []
        self.arrow_values = [0.]*5
        self.arrow_waiting = False
        self.arrow_settle = None
        self.time = 0
        self.theme = None
        self.expanded_accordions = set()
        self.deck_indices = {}
        self.armed_confirm = None
        self.component_timers = {}
        self.choice_rounds = {}
        self.asset_picker = None

    @property
    def busy(self):
        return bool(self.transition or self.page_transition or self.navigation)

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
        pt = round(size*self.prefs['text_scale'])
        if word and width:
            font = self.font(pt, word=True)
            while pt > 18 and font.size(str(text))[0] > width:
                pt -= 2
                font = self.font(pt, word=True)
        else:
            font = self.font(pt, word=word)
        rendered = self.text(font, text, width, color or self.ink)
        rect = rendered.get_rect()
        setattr(rect, {'center': 'center', 'left': 'midleft', 'right': 'midright'}[align], pos)
        surf.blit(rendered, rect)
        return rect

    def button(self, surf, rect, caption, act, **kwargs):
        rect = pygame.Rect(rect)
        if caption == '‹':
            pygame.draw.rect(surf, self.ink, rect, border_radius=12)
            x, y = rect.center
            pygame.draw.line(surf, self.bg, (x - 10, y), (x + 12, y), 3)
            pygame.draw.lines(surf, self.bg, False, [(x - 2, y - 10), (x - 12, y), (x - 2, y + 10)], 3)
            self.add(rect, act, **kwargs)
            return
        pygame.draw.rect(surf, self.ink, rect, LINE_W, border_radius=12)
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

    def logo_offsets(self, waiting):
        if not self.prefs['motion']:
            self.arrows.clear();self.arrow_settle=None;self.arrow_waiting=False
            self.arrow_values=[0.]*5
            return self.arrow_values
        if waiting:
            if not self.arrow_waiting:
                self.arrows=[dict(start=self.time,duration=random.uniform(350,950),old=value,
                                  target=random.uniform(-12,12)) for value in self.arrow_values]
            self.arrow_waiting=True;self.arrow_settle=None
            self.arrow_values=self.tween(self.arrows,[0]*5,12,self.time)
        else:
            if self.arrow_waiting:
                self.arrow_settle=(self.time,tuple(self.arrow_values))
                self.arrow_waiting=False;self.arrows.clear()
            if self.arrow_settle:
                started,values=self.arrow_settle
                t=min(1,max(0,(self.time-started)/280))
                eased=t*t*(3-2*t)
                self.arrow_values=[value*(1-eased) for value in values]
                if t>=1:self.arrow_settle=None
        return self.arrow_values

    def logo(self, surf, center, size, waiting=False):
        # A separate alpha layer preserves the black/white center of the mark.
        size = max(1, round(size)); pad = round(size*.15)
        layer = pygame.Surface(((size+pad*2)*2, (size+pad*2)*2), pygame.SRCALPHA)
        scale = size*2/140
        inset = pad*2
        offsets = self.logo_offsets(waiting)
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
            self.wheel_duration = min(650, 280 + abs(self.target-self.position)*65)
            self.wheel_start = (self.time, self.position)

    def step_selection(self, device, direction):
        self.launcher = True
        self.wheel_to(round(self.target)+direction)

    def update_wheel(self):
        if self.wheel_start:
            start, old = self.wheel_start
            t = min(1, max(0, (self.time-start)/self.wheel_duration))
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
            self.icon(surf,device.registry[index],(x,y),radius,color,fill)
            self.add((x-radius,y-radius,2*radius,2*radius),
                     'open' if index==self.selection%n and abs(distance)<.02 else 'select',
                     index=slot,app_id=device.registry[index]['id'])

    def icon(self,surf,app,center,radius,color,background=None):
        x,y=center;s=radius*.47;module=app['module'];w=max(2,round(radius/15))
        if module=='composed':
            draw_asset(surf,app_asset(app),center,radius*1.03,color,background or self.bg)
        elif module=='home':
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
        view = 'app' if device.current() else 'arc' if self.launcher else 'home'
        old = self.last_view
        # Cache both pages once; animation frames only composite two surfaces.
        changing = old != view and old is not None and 'app' in (old, view)
        if changing and self.prefs['motion']:
            outgoing = surf.copy()
            self.page_transition = None
            self._paint(surf,device,ticks,draft)
            self.page_transition = (ticks,outgoing,surf.copy(),1 if view=='app' else -1)
        elif not self.page_transition or not self.prefs['motion']:
            self.page_transition = None
            self._paint(surf,device,ticks,draft)
        if self.page_transition:
            self.time=ticks
            start,outgoing,incoming,direction=self.page_transition
            t=min(1,max(0,(ticks-start)/360))
            eased=t*t*t*(t*(t*6-15)+10)
            surf.fill(self.bg)
            surf.blit(outgoing,(round(-direction*480*eased),0))
            surf.blit(incoming,(round(direction*480*(1-eased)),0))
            self.hits.clear()
            if t>=1:
                self.page_transition=None
                self._paint(surf,device,ticks,draft)

    def _paint(self,surf,device,ticks,draft):
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
            self.response_visual(surf,device)
        elif view=='arc':self.arc(surf,device)
        elif app['module'] in ('settings','notes','clock','calculator'):
            self.utility(surf,device,app)
        else:
            self.composed_view(surf,device,app)
            if self.removed_item and self.notice_until is not None and ticks>=self.notice_until:
                self.removed_item=None;self.app_notice='';self.notice_until=None
            if self.app_notice:
                rect=pygame.Rect(24,max(self.app_body.top,min(706,self.app_body.bottom-76)),432,64)
                pygame.draw.rect(surf,self.bg,rect,border_radius=10)
                pygame.draw.rect(surf,self.ink,rect,LINE_W,border_radius=10)
                self.label(surf,self.app_notice,rect.center,16,width=420)
                self.add(rect,'undo_item' if self.removed_item else 'dismiss_notice')
        if self.asset_picker:
            from icon_picker import render as render_picker
            render_picker(self,surf,device)
        if self.keyboard:self.draw_keyboard(surf,device)

    def composed_view(self,surf,device,app):
        from components import render,control,caption,face,action_style
        self.label(surf,app['title'],(88,62),28,False,'left',290)
        control(self,surf,pygame.Rect(24,36,48,48),'','app_icon_picker')
        draw_asset(surf,app_asset(app),(48,60),30,self.ink,self.bg)
        control(self,surf,pygame.Rect(400,28,56,56),'‹','back')
        pages=app.get('pages') or [dict(id='main',title='Overview',components=[c['id'] for c in app['components']])]
        page_id=self.app_pages.get(app['id'],pages[0]['id'])
        page=next((p for p in pages if p['id']==page_id),pages[0]);self.app_pages[app['id']]=page['id']
        top=116
        if len(pages)>1:
            width=(432-8*(len(pages)-1))//len(pages)
            for index,p in enumerate(pages):
                rect=pygame.Rect(24+index*(width+8),108,width,52)
                control(self,surf,rect,p['title'],'app_page',primary=p['id']==page['id'],text=p['id'])
            top=180
        lookup={c['id']:c for c in app['components']}
        content=[lookup[cid] for cid in page['components']]
        buttons=[]
        while content and content[-1]['type'] in ('button','confirm_button') and len(buttons)<2:buttons.insert(0,content.pop())
        entry=content.pop() if buttons and content and content[-1]['type']=='input' and any(c['type'] in ('list','inventory_list','data_table','key_value_log') for c in content[:-1]) else None
        footer_height=(80 if buttons else 0)+(104 if entry else 0)
        body=pygame.Rect(0,top,480,784-top-footer_height);self.app_body=body
        layout=dict(margin=24)
        old_clip=surf.get_clip();surf.set_clip(body)
        hit_count=len(self.hits)
        y=render(self,surf,app,layout,0,body,content)
        self.scroll_limit=max(0,y+12-body.height)
        clamped=max(0,min(self.scroll,self.scroll_limit))
        if clamped!=self.scroll:
            self.scroll=clamped;del self.hits[hit_count:]
            surf.fill(self.bg,body);y=render(self,surf,app,layout,0,body,content)
        self.content_h=body.top+y+12
        surf.set_clip(old_clip)
        if self.scroll_limit:
            track=pygame.Rect(472,body.top+8,3,body.height-16)
            thumb=track.copy();thumb.height=max(28,round(track.height*body.height/(body.height+self.scroll_limit)))
            thumb.y+=round((track.height-thumb.height)*self.scroll/self.scroll_limit)
            pygame.draw.rect(surf,self.ink,thumb,border_radius=2)
        if buttons:
            footer=pygame.Rect(0,body.bottom,480,footer_height+16)
            pygame.draw.line(surf,self.ink,(24,footer.top),(456,footer.top),1)
            if entry:
                scroll=self.scroll;self.scroll=0
                render(self,surf,app,layout,12,pygame.Rect(0,footer.top,480,104),[entry]);self.scroll=scroll
            by=784-64;w=(432-12*(len(buttons)-1))//len(buttons)
            for i,c in enumerate(buttons):
                armed=c['type']=='confirm_button' and self.armed_confirm==c['action']
                primary,enabled=action_style(app,c['action'])
                control(self,surf,pygame.Rect(24+i*(w+12),by,w,56),'Confirm' if armed else c['label'],
                        'component_confirm' if c['type']=='confirm_button' else 'component_action',primary=i==0 and primary,enabled=enabled,
                        icon=component_icon(c['type'],c['label'],c.get('icon')),text=c['action'])

    def app_view(self, surf, device, app, body):
        layout = legacy.layout_of(device.modules, app.get('module'))
        y = 12
        module_name = app.get('module')
        if module_name == 'composed':
            from components import render
            y = render(self, surf, app, layout, y, body)
        elif module_name == 'checklist':
            y = self.checklist(surf, app, layout, y, body)
        elif module_name == 'scoreboard':
            y = self.scoreboard(surf, app, layout, y, body)
        elif module_name == 'progress':
            y = self.progress(surf, app, layout, y, body)
        else:
            y = self.key_value(surf, app, layout, y, body)
        self.content_h = body.top + y + 8

    def response_visual(self, surf, device):
        speaking=device.agent=='listening'
        mode='speech' if speaking or device.agent=='thinking' else 'response'
        text=self.listening_text if speaking else self.submitted_text if device.agent=='thinking' else device.say
        preview=mode=='speech'
        font=self.font(round((20 if preview else 22)*self.prefs['text_scale']))
        if mode!=self.text_mode:
            self.transcript.clear();self.text_mode=mode
            self.response_source=None
        if mode=='response':
            if text!=self.response_source:
                self.response_source=text;self.response_started=self.time
            self.response_target=short_response(text,lambda value:font.size(value)[0])
            text=self.response_target
            words=text.split()
            interval=42 if self.prefs['motion'] else 0
            count=min(len(words),1+int((self.time-self.response_started)/interval)) if interval else len(words)
            text=' '.join(words[:count])
        line_height=round((24 if preview else 28)*self.prefs['text_scale'])
        height=90 if preview else 66
        self.transcript.update(text,self.time,lambda value:font.size(value)[0],
                               line_height=line_height,animate=self.prefs['motion'],align='center',
                               visible_lines=3 if preview else 1)
        if not text:return
        # Each line remains centered; position changes ease as the text grows.
        # Evolving ASR hypotheses and response words share the same soft reveal.
        layer=pygame.Surface((408,height),pygame.SRCALPHA)
        for word,x,y,opacity in self.transcript.frames(self.time):
            if opacity<=0 or y < -line_height or y>=height:continue
            glyph=font.render(word,True,self.ink)
            glyph.set_alpha(round(255*opacity))
            layer.blit(glyph,(round(x),round(y)+4))
        if self.transcript.scroll(self.time)>1:
            mask=pygame.Surface(layer.get_size(),pygame.SRCALPHA)
            mask.fill((255,255,255,255))
            for row in range(8):
                pygame.draw.line(mask,(255,255,255,round(row/7*255)),(0,row),(408,row))
            layer.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(layer,(36,534 if preview else 556))

    def utility(self,surf,device,app):
        self.label(surf,app['title'],(40,100),32,True,'left',330)
        self.button(surf,(388,70,56,56),'‹','back')
        module=app['module']
        if module=='settings':
            prefs=self.prefs
            generated=sum(a['id'] not in {id for id,_,_ in BUILTINS} for a in device.registry)
            if self.delete_apps_confirm:
                self.label(surf,'Delete generated apps?',(240,206),22,width=432)
                self.label(surf,f'This removes {generated} generated apps.',(240,254),17,width=432)
                self.label(surf,'Default apps and Notes stay.',(240,286),17,width=432,color=legacy.MUTED)
                self.button(surf,(24,340,208,64),'Cancel','delete_apps_cancel')
                self.button(surf,(248,340,208,64),'Delete apps','delete_apps_confirm')
                return
            rows=[('Appearance','Dark' if prefs['theme']=='dark' else 'Light'),
                  ('Motion','On' if prefs['motion'] else 'Reduced'),
                  ('Delete generated apps',f'{generated} apps' if generated else 'No generated apps')]
            for index,(label,value) in enumerate(rows):
                rect=pygame.Rect(24,180+index*88,432,72)
                pygame.draw.rect(surf,self.bg,rect,border_radius=12)
                pygame.draw.rect(surf,self.ink,rect,LINE_W,border_radius=12)
                self.label(surf,label,(42,rect.y+23),18,align='left',width=240)
                self.label(surf,value,(438,rect.y+50),16,align='right',width=200,color=legacy.MUTED)
                if index==2:
                    draw_asset(surf,'trash',(rect.right-42,rect.y+25),26,self.ink if generated else legacy.MUTED,self.bg)
                    if generated:self.add(rect,'setting',index=index)
                    continue
                active=(prefs['theme']=='dark') if index==0 else bool(prefs['motion'])
                track=pygame.Rect(rect.right-66,rect.y+12,48,24)
                pygame.draw.rect(surf,self.ink if active else self.bg,track,border_radius=12)
                pygame.draw.rect(surf,self.ink,track,LINE_W,border_radius=12)
                pygame.draw.circle(surf,self.bg if active else self.ink,(track.right-12 if active else track.left+12,track.centery),7)
                self.add(rect,'setting',index=index)
        elif module=='notes':
            text=app['state'].get('text','')
            words=len(text.split()) if text.strip() else 0
            banner=pygame.Rect(24,154,432,46)
            pygame.draw.rect(surf,self.ink,banner,border_radius=10)
            self.label(surf,'NOTEBOOK',(40,banner.centery),15,True,'left',240,color=self.bg)
            self.label(surf,f'{words} words',(440,banner.centery),15,True,'right',160,color=self.bg)
            lines=[]
            for paragraph in (text or 'Tap to write a note…').split('\n'):
                line=''
                for word in paragraph.split(' '):
                    if self.font(20).size(line+' '+word)[0]>396:
                        lines.append(line);line=word
                    else:line=(line+' '+word).strip()
                lines.append(line)
            area=pygame.Rect(24,212,432,520)
            pygame.draw.rect(surf,self.bg,area,border_radius=12)
            pygame.draw.rect(surf,self.ink,area,LINE_W,border_radius=12)
            surf.set_clip(area.inflate(-4,-4))
            for i,line in enumerate(lines):
                ry=238+i*36-self.scroll
                self.label(surf,line,(42,ry),20,align='left',width=396,color=self.ink if text else legacy.MUTED)
                pygame.draw.line(surf,legacy.CARD,(38,ry+18),(442,ry+18),LINE_W)
            surf.set_clip(None);self.content_h=max(726,len(lines)*36+220)
            self.add(area,'edit_notes')
        elif module=='clock':
            now=datetime.datetime.now();pattern='%H:%M' if self.prefs['clock24'] else '%I:%M %p'
            tbox=pygame.Rect(24,176,432,190)
            pygame.draw.rect(surf,self.bg,tbox,border_radius=14)
            pygame.draw.rect(surf,self.ink,tbox,LINE_W,border_radius=14)
            self.label(surf,'LOCAL TIME',(240,204),14,True,color=legacy.MUTED)
            self.label(surf,now.strftime(pattern),(240,272),56,True,width=410)
            track=pygame.Rect(48,334,384,12)
            pygame.draw.rect(surf,self.ink,track,LINE_W,border_radius=6)
            fill_w=round(380*(now.second/59.0)) if now.second else 4
            pygame.draw.rect(surf,self.ink,(track.x+2,track.y+2,fill_w,8),border_radius=4)
            c1=pygame.Rect(24,382,210,82);c2=pygame.Rect(246,382,210,82)
            for card,cap,val in ((c1,'DATE',now.strftime('%a, %b %d')),(c2,'ZONE',time.tzname[time.localtime().tm_isdst])):
                pygame.draw.rect(surf,self.bg,card,border_radius=12)
                pygame.draw.rect(surf,self.ink,card,LINE_W,border_radius=12)
                self.label(surf,cap,(card.x+14,card.y+22),13,True,'left',180,color=legacy.MUTED)
                self.label(surf,val,(card.x+14,card.y+54),19,align='left',width=182)
            self.button(surf,(140,580,200,58),'24-hour' if self.prefs['clock24'] else '12-hour','clock_format')
        else:
            disp=pygame.Rect(24,158,432,86)
            pygame.draw.rect(surf,self.bg,disp,border_radius=12)
            pygame.draw.rect(surf,self.ink,disp,LINE_W,border_radius=12)
            self.label(surf,'ACCUMULATOR',(40,180),12,True,'left',200,color=legacy.MUTED)
            self.label(surf,self.calculator or '0',(438,214),38,True,'right',400)
            rows=[['C','±','⌫','÷'],['7','8','9','×'],['4','5','6','−'],['1','2','3','+'],['0','.','=']]
            for row,keys in enumerate(rows):
                for col,key in enumerate(keys):
                    self.button(surf,(24+col*110,280+row*88,212 if key=='=' else 102,76),key,'calc',text=key)

    def draw_keyboard(self,surf,device):
        # The keyboard owns its covered area, including the gaps between keys.
        covered=pygame.Rect(0,365,480,435)
        self.hits=[hit for hit in self.hits if not hit.rect.colliderect(covered)]
        pygame.draw.rect(surf,self.bg,(0,365,480,435))
        pygame.draw.line(surf,self.ink,(0,365),(480,365),LINE_W)
        text=self.keyboard['text']
        if self.app_notice:self.label(surf,self.app_notice,(24,416),12,align='left',width=432)
        placeholder={'notes':'Write a note','request':'Describe an app','component':'Enter text','item':'Edit entry','number':'Enter a number','icon_search':'Search icons'}[self.keyboard['kind']]
        self.label(surf,text[-44:] or placeholder,(24,397),18,align='left',width=432)
        if self.keyboard['kind']=='number':
            for row,keys in enumerate(('789','456','123','-0.')):
                for col,key in enumerate(keys):
                    self.button(surf,(24+col*148,430+row*66,136,56),key,'key',text=key)
            for col,label,key in ((0,'⌫','backspace'),(1,'Clear','clear'),(2,'Done','done')):
                self.button(surf,(24+col*148,704,136,64),label,'key',text=key)
            self.hits=[hit for hit in self.hits if hit.act=='key'];return
        for row,keys in enumerate(('1234567890','qwertyuiop','asdfghjkl','zxcvbnm')):
            width=48;left=(480-len(keys)*width)/2
            for col,key in enumerate(keys):
                self.button(surf,(left+col*width,430+row*62,width-4,54),key.upper() if self.keyboard_shift else key,'key',text=key.upper() if self.keyboard_shift else key)
        self.button(surf,(12,616,64,54),'Aa','key',text='shift')
        self.button(surf,(404,616,64,54),'.','key',text='.')
        for x,w,label,key in [(12,90,'⌫','backspace'),(108,90,'↵','newline'),(204,150,'space',' '),(360,108,'Done','done')]:
            self.button(surf,(x,690,w,60),label,'key',text=key)
        for index,key in enumerate((',',':','-','/','@','Clear')):
            self.button(surf,(2+index*80,752,76,44),key,'key',text='clear' if key=='Clear' else key)
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
            for key,choices in dict(theme=('dark','light'),motion=(True,False),clock24=(True,False)).items():
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
        generated=[app for app in self.device.registry if isinstance(app,dict) and app.get('id') not in builtin_ids and isinstance(app.get('state'),dict)]
        migrated=[]
        if generated:
            backup=store.with_name('registry.pre-components.json')
            if not backup.exists():backup.write_text(json.dumps(self.device.snapshot(),indent=2))
        for app in generated:
            try:migrated.append(to_composed(app))
            except (ContractError,KeyError,ValueError,TypeError):
                print('Skipped invalid saved app: %s (original registry backed up)' % app.get('id'),flush=True)
        self.device.registry=builtins+migrated
        self.device.go_home();self.device.save(store)
        self.screen=NativeScreen(self.prefs)
        self.stub=stub;self.turn=turn if kiosk else 'none';self.kiosk=kiosk
        self.backend=backend or ('stub' if live else 'demo');self.live=self.backend!='demo'
        self.recorder=legacy.AudioRecorder()
        self.draft='';self.events=legacy.queue.Queue();self.press=None;self.stopping=False
        self.phone=pygame.Surface((480,800))
        self.pending=None;self.request_number=0;self.after_response=None;self.response_ready_at=None;self.deferred_effect=None
        self.speech_preview=None;self.speech_segments=[]
        self.speech=speech;self.speech_session=None;self.speech_finalizing=False

    def save_preferences(self):
        self.preferences_path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.preferences_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.prefs,indent=2));temporary.replace(self.preferences_path)

    def set_launcher(self, value, clear_response=True):
        self.screen.asset_picker=None
        self.screen.delete_apps_confirm=False
        self.device.go_home();self.screen.launcher=value;self.screen.scroll=0
        if not value and clear_response:
            self.device.say='';self.device.respond_until=None
            self.screen.transcript.clear();self.screen.response_source=None
            self.screen.text_mode=None
        self.device.save(self.store)

    def send(self,text="",wav_base64=None):
        text=(text or '').strip()
        if (not text and not wav_base64) or self.pending or self.after_response:return
        self.screen.submitted_text=text
        self.draft='';self.screen.keyboard=None;self.screen.wave.clear()
        self.set_launcher(False,clear_response=False)
        self.screen.text_mode='speech';self.screen.response_source=None
        self.device.agent='thinking';self.device.say='';self.device.respond_until=None
        self.request_number+=1
        local=match_command(text,self.prefs,self.device.registry)
        due=time.monotonic()+(0 if self.live or local else self.prefs['wait_seconds'])
        self.pending=dict(request=text or 'Voice request',due=due,number=self.request_number)
        if local:
            self.pending['local']=True
            self.pending['effect']=local.effect
            self.events.put((self.request_number,local.turn))
            return
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
                result=error
            self.events.put((number,result))
            return
        try:self.events.put((number,legacy.post_json(self.stub,payload)))
        except (OSError,ValueError):self.events.put((number,None))

    def select_app(self,app):
        if 'title' in app and isinstance(app['title'],str):
            app['title']=app['title'][:16].strip()
        base=app['id'];suffix=2
        while self.device.find(app['id']):app['id']=f'{base}_{suffix}';suffix+=1
        self.device.registry.append(app)
        index=len(self.device.registry)-1
        self.screen.selection=index;self.screen.position=self.screen.target=float(index);self.screen.wheel_start=None
        self.device.agent='idle';self.device.say='';self.set_launcher(True)

    def navigate_app(self, app_id):
        if not self.prefs['motion']:
            self.device.open_app(app_id)
            self.screen.launcher=True;self.screen.scroll=0
            index=next(i for i,a in enumerate(self.device.registry) if a['id']==app_id)
            self.screen.position=self.screen.target=float(index);self.screen.selection=index
            self.device.save(self.store)
            return
        index=next(i for i,a in enumerate(self.device.registry) if a['id']==app_id)
        # Start at a real app maximally distant around the circular registry.
        start=(index+len(self.device.registry)//2)%len(self.device.registry)
        self.screen.position=self.screen.target=float(start);self.screen.selection=start
        self.screen.wheel_start=None
        self.set_launcher(True)
        self.screen.navigation=dict(app_id=app_id,stage='arrive')

    def poll_navigation(self):
        screen=self.screen;route=screen.navigation
        if not route:return
        if screen.transition or screen.page_transition or screen.last_view!='arc':return
        if route['stage']=='arrive':
            index=next(i for i,a in enumerate(self.device.registry) if a['id']==route['app_id'])
            n=len(self.device.registry)
            # Rotate the shortest distance, including across the end of the list.
            target=screen.position+(index-screen.position+n/2)%n-n/2
            screen.wheel_to(target)
            route['stage']='rotate'
        elif not screen.wheel_start:
            if route['stage']=='rotate':
                route.update(stage='focus',until=screen.time+120)
            elif screen.time>=route['until']:
                screen.navigation=None
                self.device.open_app(route['app_id']);screen.scroll=0
                self.device.save(self.store)

    def poll_response(self):
        turn=self.after_response
        if turn is None:return
        screen=self.screen
        if (screen.last_view!='home' or screen.transition or screen.page_transition or
                screen.text_mode!='response' or screen.response_source!=turn['say'] or
                screen.transcript.text!=screen.response_target or
                not screen.transcript.settled(screen.time)):
            self.response_ready_at=None;return
        # Start the action only after actual rendered text has finished revealing
        # and remained readable. Do not count backend or hidden-screen time.
        if self.response_ready_at is None:self.response_ready_at=screen.time
        if screen.time < self.response_ready_at+1200:return
        self.after_response=None
        effect=self.deferred_effect;self.deferred_effect=None
        if effect:self.apply_local_effect(effect)
        else:self.apply_result(turn)

    def apply_local_effect(self,effect):
        if effect['kind']=='preference':
            self.prefs[effect['key']]=effect['value']
            self.save_preferences()
            print('Preference applied: %s=%s' % (effect['key'],effect['value']),flush=True)
        elif effect['kind']=='note':
            app=self.device.find('notes')
            previous=app['state'].get('text','')
            app['state']['text']=previous+('\n' if previous else '')+effect['text']
            self.device.save(self.store);self.navigate_app('notes')
        elif effect['kind']=='calculation':
            self.screen.calculator=effect['value'];self.navigate_app('calculator')

    def tick_component_timers(self):
        changed=False
        for key,timer in self.screen.component_timers.items():
            if not timer.get('running'):continue
            app_id,field_id=key.split(':',1);app=self.device.find(app_id)
            if not app:timer['running']=False;continue
            f=fields(app).get(field_id)
            if not f or f['type']!='number':timer['running']=False;continue
            remaining=max(f['min'],min(f['max'],timer['base']-max(0,(self.screen.time-timer['started'])//1000)))
            if f['value']!=remaining:f['value']=remaining;changed=True
            if remaining<=f['min']:timer['running']=False
        if changed:self.device.save(self.store)

    def poll(self):
        self.tick_component_timers()
        self.poll_response()
        self.poll_navigation()
        self.poll_speech()
        if not self.pending:return
        while not self.events.empty():
            number,result=self.events.get_nowait()
            if number==self.pending['number']:self.pending['result']=result
        if time.monotonic()<self.pending['due']:return
        if self.live and 'result' not in self.pending:return
        pending=self.pending;self.pending=None
        if pending.get('local'):
            result=pending['result']
        elif not self.live:
            request=pending['request']
            navigate=preview_navigation(request,self.device.registry)
            if navigate:result=navigate
            elif request.lower().lstrip().startswith(('what ','why ','how ','when ','where ','who ','is ','are ')):
                result=message('This is the offline preview. Enable Gemini for answers.')
            elif any(word in request.lower() for word in ('create','make','build','list','shop','water','hydrat','score','timer')):
                result={'schema_version':2,'intent':'create_app','op':'propose','say':'Your app is ready.',
                        'app':demo_app(request,self.device.registry)}
            else:result=message('This is the offline preview. Enable Gemini for answers.')
        else:result=pending['result']
        if isinstance(result,Exception):
            self.device.agent='idle';self.device.say=str(result);speak(str(result));return
        try:validate_turn(result,self.device.registry)
        except (ContractError,TypeError):
            self.device.agent='idle';self.device.say='The response could not be used. Please try again.'
            speak(self.device.say);return
        self.device.last_turn=copy.deepcopy(result)
        self.device.agent='idle';self.device.say=result['say'];speak(result['say'])
        self.device.save(self.store)
        self.deferred_effect=pending.get('effect')
        if self.deferred_effect or result['op'] in ('navigate','propose','mutate'):
            self.after_response=copy.deepcopy(result);self.response_ready_at=None
        # Messages stay here; app changes wait for their response to be read.

    def apply_result(self,result):
        if result['op']=='navigate':
            self.device.agent='idle';self.device.say=result['say']
            destination=result['destination']
            if destination in ('agent','apps'):self.set_launcher(destination=='apps')
            else:
                app_id=result['app_id'] if destination=='app' else destination
                self.navigate_app(app_id)
            return
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
        self.device.say=result['say']
        self.device.save(self.store)

    def change_setting(self,index):
        self.screen.setting_cursor=index
        if index==2:
            self.screen.delete_apps_confirm=any(a['id'] not in {id for id,_,_ in BUILTINS} for a in self.device.registry)
            return
        if index==0:self.prefs['theme']='light' if self.prefs['theme']=='dark' else 'dark'
        elif index==1:
            self.prefs['motion']=not self.prefs['motion']
            if not self.prefs['motion']:
                self.screen.transition=None;self.screen.position=self.screen.target;self.screen.wheel_start=None
        self.save_preferences()

    def delete_generated_apps(self):
        app=self.device.current()
        if not self.screen.delete_apps_confirm or not app or app['id']!='settings':return
        builtin_ids={id for id,_,_ in BUILTINS}
        self.device.registry=[a for a in self.device.registry if a['id'] in builtin_ids]
        self.device.last_turn=None;self.device.proposal=None
        self.screen.delete_apps_confirm=False
        self.screen.component_timers.clear();self.screen.choice_rounds.clear()
        self.screen.app_pages.clear();self.screen.page_scroll.clear()
        self.screen.removed_item=None;self.screen.app_notice='';self.screen.notice_until=None
        self.screen.keyboard=None;self.screen.asset_picker=None;self.screen.scroll=0
        index=next(i for i,a in enumerate(self.device.registry) if a['id']=='settings')
        self.screen.selection=index;self.screen.position=self.screen.target=float(index)
        self.screen.wheel_start=None
        self.device.save(self.store)

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
        if key=='clear':
            keyboard['text']=''
            if keyboard['kind']=='notes':self.device.find('notes')['state']['text']='';self.device.save(self.store)
            return
        if key=='done':
            if keyboard['kind']=='icon_search' and self.screen.asset_picker:
                self.screen.asset_picker.update(query=keyboard['text'][:80],page=0)
            if keyboard['kind'] in ('number','item','component'):
                app=self.device.find(keyboard['app_id'])
                try:
                    if keyboard['kind']=='number':value=float(keyboard['text'])
                    elif keyboard['kind']=='component':value=keyboard['text'][:2000]
                    else:
                        value=copy.deepcopy(fields(app)[keyboard['field_id']]['value'])
                        value[keyboard['index']]['label']=keyboard['text'].strip()
                    updated=apply_operations(app,[dict(action='set',target=keyboard['field_id'],value=value)])
                except ValueError:
                    self.screen.app_notice='Enter a valid number.';return
                except ContractError as error:
                    self.screen.app_notice=str(error);return
                app['state']=updated['state'];self.device.save(self.store);self.screen.app_notice=''
            if keyboard['kind']=='request':self.draft=keyboard['text']
            self.screen.keyboard=None;return
        if key=='backspace':keyboard['text']=keyboard['text'][:-1]
        else:keyboard['text']+= '\n' if key=='newline' else key
        if keyboard['kind']=='notes':
            self.device.find('notes')['state']['text']=keyboard['text'];self.device.save(self.store)
        elif keyboard['kind']=='component':
            keyboard['text']=keyboard['text'][:2000]
        elif keyboard['kind']=='request':self.draft=keyboard['text']

    def activate(self,hit):
        if hit is None or self.pending or self.after_response or self.screen.busy:return
        act=hit.act
        if act=='delete_apps_cancel':self.screen.delete_apps_confirm=False;return
        if act=='delete_apps_confirm':self.delete_generated_apps();return
        if self.screen.delete_apps_confirm and act!='back':return
        if self.screen.asset_picker and not (act.startswith('asset_') or act=='key'):return
        if act=='app_icon_picker':
            app=self.device.current()
            if app and app['module']=='composed':self.screen.asset_picker=dict(app_id=app['id'],query='',page=0)
            return
        if act.startswith('asset_'):
            picker=self.screen.asset_picker
            if not picker:return
            if act=='asset_close':self.screen.asset_picker=None;self.screen.keyboard=None
            elif act=='asset_page':picker['page']+=hit.amount
            elif act=='asset_search':self.screen.keyboard=dict(kind='icon_search',text=picker['query'])
            elif act in ('asset_select','asset_auto'):
                app=self.device.find(picker['app_id'])
                if app:
                    updated=copy.deepcopy(app)
                    if act=='asset_select':updated['icon']=hit.text
                    else:updated.pop('icon',None)
                    try:validate_app(updated)
                    except ContractError:return
                    app.clear();app.update(updated);self.device.save(self.store)
                self.screen.asset_picker=None
                self.screen.keyboard=None
            return
        if act=='undo_item':
            saved=self.screen.removed_item
            if saved:
                app_id,field_id,index,item=saved;app=self.device.find(app_id)
                value=copy.deepcopy(fields(app)[field_id]['value'])
                value.insert(min(index,len(value)),item)
                try:updated=apply_operations(app,[dict(action='set',target=field_id,value=value)])
                except ContractError as error:self.screen.app_notice=str(error);return
                app['state']=updated['state'];self.device.save(self.store)
            self.screen.removed_item=None;self.screen.app_notice='';return
        if act=='app_page':
            app=self.device.current()
            if app and any(p['id']==hit.text for p in app.get('pages',[])):
                old=self.screen.app_pages.get(app['id'],app['pages'][0]['id'])
                self.screen.page_scroll[(app['id'],old)]=self.screen.scroll
                self.screen.app_pages[app['id']]=hit.text
                self.screen.scroll=self.screen.page_scroll.get((app['id'],hit.text),0)
                self.screen.armed_confirm=None;self.screen.app_notice=''
            return
        if act=='dismiss_notice':self.screen.app_notice='';return
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
        if act!='component_confirm':self.screen.armed_confirm=None
        if act.startswith('component_'):
            app=self.device.current()
            if app is None or app.get('module')!='composed':return
            if act=='component_accordion':
                if hit.text in self.screen.expanded_accordions:self.screen.expanded_accordions.remove(hit.text)
                else:self.screen.expanded_accordions.add(hit.text)
                return
            if act=='component_deck_nav':
                self.screen.deck_indices[hit.text]=self.screen.deck_indices.get(hit.text,0)+hit.amount
                return
            if act=='component_confirm':
                if self.screen.armed_confirm!=hit.text:
                    self.screen.armed_confirm=hit.text;return
                self.screen.armed_confirm=None
                act='component_action'
            state=fields(app)
            game_round=None
            if act=='component_game':
                from choice_game import REVEAL_MS
                component=next((c for c in app['components'] if c['id']==hit.text and c['type']=='choice_game'),None)
                if component is None or not 0<=hit.index<len(component['choices']):return
                key=app['id']+':'+component['id'];previous=self.screen.choice_rounds.get(key)
                if previous and self.prefs['motion'] and self.screen.time-previous['started']<REVEAL_MS:return
                operation={name:component[name] for name in ('player','opponent','wins','losses','draws','choices')}
                operation.update(action='play_choice',target=component['bind'],choice=component['choices'][hit.index]['id'])
                game_round=(key,dict(started=self.screen.time,before={k:copy.deepcopy(f['value']) for k,f in state.items()}))
            if act in ('component_number_input','component_item_edit'):
                value=state[hit.text]['value']
                self.screen.keyboard=dict(kind='number' if act=='component_number_input' else 'item',
                    text=str(value) if act=='component_number_input' else value[hit.index]['label'],
                    app_id=app['id'],field_id=hit.text,index=hit.index)
                return
            if act=='component_item_remove':
                value=copy.deepcopy(state[hit.text]['value']);removed=value.pop(hit.index)
                operation={'action':'set','target':hit.text,'value':value}
            elif act=='component_input':
                self.screen.keyboard=dict(kind='component',text=state[hit.text]['value'],app_id=app['id'],field_id=hit.text)
                return
            if act in ('component_item_remove','component_game'):pass
            elif act=='component_action':
                operation=next(action for action in app['actions'] if action['id']==hit.text)
                operation={key:value for key,value in operation.items() if key!='id'}
            elif act=='component_toggle':operation={'action':'toggle','target':hit.text}
            elif act in ('component_step','component_set_num','component_random','component_xy'):
                f=state[hit.text]
                lo,hi=f['min'],f['max']
                if act=='component_step':raw=f['value']+hit.amount
                elif act=='component_set_num':raw=hit.amount
                elif act=='component_random':raw=random.randint(int(lo),int(hi)) if lo==int(lo) and hi==int(hi) else random.uniform(lo,hi)
                else:
                    px=getattr(self,'release_position',None)
                    px=px[0] if px else hit.rect.centerx
                    ratio=max(0.0,min(1.0,(px-hit.rect.x-20)/max(1,hit.rect.width-40)))
                    raw=round(lo+ratio*(min(hi,hit.amount)-lo))
                val=max(lo,min(hi,raw))
                if isinstance(f['value'],int) and val==int(val):val=int(val)
                operation={'action':'set','target':hit.text,'value':val}
            elif act in ('component_timer_toggle','component_timer_reset'):
                f=state[hit.text]
                t_key=f"{app['id']}:{hit.text}"
                t_state=self.screen.component_timers.get(t_key)
                if act=='component_timer_toggle':
                    if t_state and t_state.get('running'):
                        elapsed=max(0,(self.screen.time-t_state['started'])//1000)
                        rem=max(int(f['min']),min(int(f['max']),t_state['base']-elapsed))
                        t_state['running']=False;t_state['base']=rem
                        operation={'action':'set','target':hit.text,'value':rem}
                    else:
                        base=int(f['value']) if int(f['value'])>0 else max(int(f['min']),min(int(f['max']),60))
                        init_val=t_state.get('initial',base) if t_state else base
                        self.screen.component_timers[t_key]=dict(running=True,started=self.screen.time,base=base,initial=init_val)
                        return
                else:
                    init_val=t_state.get('initial',int(f['value'])) if t_state else int(f['value'])
                    self.screen.component_timers.pop(t_key,None)
                    operation={'action':'set','target':hit.text,'value':max(int(f['min']),min(int(f['max']),init_val))}
            elif act=='component_item':
                value=copy.deepcopy(state[hit.text]['value']);value[hit.index]['checked']=not value[hit.index]['checked']
                operation={'action':'set','target':hit.text,'value':value}
            elif act=='component_radio':
                value=copy.deepcopy(state[hit.text]['value'])
                for idx,it in enumerate(value):it['checked']=(idx==hit.index)
                operation={'action':'set','target':hit.text,'value':value}
            elif act=='component_item_qty':
                from components import _item_qty
                value=copy.deepcopy(state[hit.text]['value'])
                name,qty=_item_qty(value[hit.index]['label'])
                new_qty=max(0,qty+hit.amount)
                value[hit.index]['label']=f"{name} ×{new_qty}"
                value[hit.index]['checked']=new_qty>0
                operation={'action':'set','target':hit.text,'value':value}
            else:return
            try:updated=apply_operations(app,[operation])
            except ContractError as error:
                self.screen.app_notice=str(error);return
            self.screen.app_notice='';self.screen.removed_item=None
            if act=='component_item_remove':
                self.screen.removed_item=(app['id'],hit.text,hit.index,removed)
                self.screen.app_notice='Entry removed. Tap to undo.'
                self.screen.notice_until=self.screen.time+4000
            if game_round:self.screen.choice_rounds[game_round[0]]=game_round[1]
            else:
                for key in list(self.screen.choice_rounds):
                    if key.startswith(app['id']+':'):self.screen.choice_rounds.pop(key)
            app['state']=updated['state'];self.device.save(self.store);return
        super().activate(hit)

    def on_down(self,pos):
        if pos is None or self.pending or self.after_response or self.speech_session is not None or self.screen.busy:return
        hit=self.screen.at(pos)
        now=pygame.time.get_ticks();self.screen.time=now
        self.press=dict(x=pos[0],y=pos[1],hit=hit,time=now,talk=bool(hit and hit.act=='talk'),moved=False,
                        scroll=self.screen.scroll)
        app=self.device.current()
        self.press['scrollable']=bool(not self.screen.keyboard and not self.screen.asset_picker and app and
            app['module'] in ('notes','composed') and
            (app['module']!='composed' or self.screen.app_body.collidepoint(pos)) and
            (hit is None or hit.act=='edit_notes' or hit.act.startswith('component_')))
        if hit and hit.act=='component_xy':self.press['slider']=True
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
        if not press or pos is None or press['talk']:return
        if press.get('slider'):
            app=self.device.current();hit=press['hit'];f=fields(app)[hit.text]
            ratio=max(0,min(1,(pos[0]-hit.rect.x-20)/max(1,hit.rect.width-40)))
            self.screen.slider_preview=(app['id'],hit.text,round(f['min']+ratio*(min(f['max'],hit.amount)-f['min'])))
            return
        if press['hit'] and not press.get('wheel') and not press['scrollable']:
            # Fixed controls own their gesture, including keyboard keys.
            if not press['hit'].rect.inflate(TOUCH_PADDING*2,TOUCH_PADDING*2).collidepoint(pos):
                press['moved']=True
            return
        if not press['moved'] and math.hypot(pos[0]-press['x'],pos[1]-press['y'])<TOUCH_SLOP:return
        press['moved']=True
        if press.get('wheel'):
            angle=math.atan2(pos[1]-CY,pos[0]-CX)
            delta=math.atan2(math.sin(angle-press['angle']),math.cos(angle-press['angle']))
            press['angle']=angle
            self.screen.position-=delta/STEP;self.screen.target=self.screen.position
            self.screen.selection=round(self.screen.position)
        elif press['scrollable']:
            app=self.device.current()
            limit=self.screen.scroll_limit if app and app['module']=='composed' else max(0,self.screen.content_h-726)
            self.screen.scroll=min(limit,max(0,press['scroll']-(pos[1]-press['y'])))

    def cancel_press(self):
        self.screen.slider_preview=None
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
        self.release_position=pos
        if press.get('slider'):
            self.screen.slider_preview=None
            if pos is not None:self.activate(press['hit'])
            return
        if press['talk']:
            should_send=pos is not None and pygame.time.get_ticks()-press['time']>=350
            if self.speech and self.speech_session is not None:
                if should_send:
                    self.speech_finalizing=True
                    self.screen.submitted_text=self.screen.listening_text
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
        if not press['moved'] and pos is not None and press['hit']:
            original=press['hit'];hit=self.screen.at(pos)
            # Hits are rebuilt every frame. Compare the complete control identity,
            # then activate the original control, never the one under a drifting finger.
            same=hit is None or vars(hit)==vars(original)
            if same and original.rect.inflate(TOUCH_PADDING*2,TOUCH_PADDING*2).collidepoint(pos):
                self.activate(original)

    def scroll_input(self,direction):
        if self.pending or self.after_response or self.speech_session is not None or self.screen.busy or self.screen.keyboard:return
        if self.screen.asset_picker:
            self.screen.asset_picker['page']+=direction;return
        app=self.device.current()
        if app and app['module']=='settings':self.screen.setting_cursor=(self.screen.setting_cursor+direction)%SETTINGS_COUNT
        elif app:
            limit=self.screen.scroll_limit if app['module']=='composed' else max(0,self.screen.content_h-726)
            self.screen.scroll=max(0,min(limit,self.screen.scroll+direction*48))
        else:self.screen.step_selection(self.device,direction)

    def on_key(self,event):
        mods=event.mod;ctrl=bool(mods & (pygame.KMOD_CTRL|pygame.KMOD_META))
        if ctrl and event.key==pygame.K_q and mods & pygame.KMOD_SHIFT:return 'quit'
        if event.key==pygame.K_ESCAPE:
            if self.after_response is not None:
                self.after_response=None;self.deferred_effect=None;self.set_launcher(False);return
            if self.screen.navigation:
                self.screen.navigation=None;self.set_launcher(True);return
            if self.speech_session is not None:self.cancel_press()
            elif self.screen.keyboard:self.screen.keyboard=None
            elif self.screen.delete_apps_confirm:self.screen.delete_apps_confirm=False
            elif self.screen.asset_picker:self.screen.asset_picker=None
            elif self.pending:
                self.request_number+=1;self.pending=None;self.device.agent='idle';self.device.say=''
            elif self.device.current():self.set_launcher(True)
            elif self.screen.launcher:self.set_launcher(False)
            return
        if self.pending or self.after_response or self.speech_session is not None or self.screen.busy:return
        if self.screen.delete_apps_confirm:
            if event.key==pygame.K_RETURN:self.screen.delete_apps_confirm=False
            return
        if self.screen.asset_picker and not self.screen.keyboard:
            picker=self.screen.asset_picker
            if event.key==pygame.K_BACKSPACE:picker.update(query=picker['query'][:-1],page=0)
            elif event.key in (pygame.K_LEFT,pygame.K_RIGHT):picker['page']+=-1 if event.key==pygame.K_LEFT else 1
            elif event.key==pygame.K_RETURN:self.screen.keyboard=dict(kind='icon_search',text=picker['query'])
            return
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
        if self.pending or self.after_response or self.speech_session is not None or self.screen.busy or not text:return
        if self.screen.keyboard:self.keyboard_key(text);return
        if self.screen.asset_picker:
            picker=self.screen.asset_picker;picker.update(query=(picker['query']+text)[:80],page=0);return
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

        Empty provisional hypotheses must not erase words already on screen.
        Keep draining the current session after release, until its authoritative
        final result replaces the preview. Cancelled/stale sessions are filtered
        by poll_speech before reaching this method.
        """
        if self.device.agent != 'listening' and not self.speech_finalizing:
            return
        if 'text' in result:
            text=str(result['text']).strip()
            if not text:return
            self.speech_segments.append(text)
            partial=''
        elif 'partial' in result:
            partial=str(result['partial']).strip()
            if not partial:return
        else:
            return
        self.screen.listening_text=' '.join(self.speech_segments+([partial] if partial else []))
        if self.speech_finalizing:
            self.screen.submitted_text=self.screen.listening_text

    def update_speech_preview(self, ticks):
        if self.press and self.press['talk'] and self.speech_preview:
            result=self.speech_preview.partial_result(ticks-self.press['time'])
            self.apply_speech_result(result)

    def frame(self,display):
        ticks=pygame.time.get_ticks()
        self.screen.time=ticks
        self.update_speech_preview(ticks)
        super().frame(display)
