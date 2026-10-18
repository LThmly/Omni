"""Shared app design system: readable content, real controls, and bounded layout."""
import math
import re
import pygame
import phone as ui
from contract.runtime import fields
from contract.asset_catalog import component_icon
from icon_assets import draw as draw_asset

GAP=16
MIN_TOUCH=48


def _split_kv(label):
    for sep in (' · ',' — ',': ',' - ','|'):
        if sep in label:return tuple(part.strip() for part in label.split(sep,1))
    return label,''


def _item_qty(label):
    match=re.search(r'(?:×|x|:|\s)(\d+)\s*$',label)
    return (label[:match.start()].rstrip(' :×x-') or label,int(match[1])) if match else (label,1)


def face(screen,size=18,bold=False):
    return screen.font(round(size*min(1.15,screen.prefs.get('text_scale',1))),bold=bold)


def lines(screen,text,width,size=18,bold=False):
    cache=getattr(screen,'app_line_cache',None)
    if cache is None:cache={};screen.app_line_cache=cache
    key=(str(text),width,size,bold,screen.prefs.get('text_scale',1))
    if key in cache:return cache[key]
    font=face(screen,size,bold);result=[]
    for paragraph in str(text).split('\n'):
        line=''
        for word in paragraph.split():
            # Split long tokens rather than silently ellipsizing the content.
            if line and font.size(line+' '+word)[0]>width:result.append(line);line=''
            while font.size(word)[0]>width:
                n=1
                while n<len(word) and font.size(word[:n+1])[0]<=width:n+=1
                if line:result.append(line);line=''
                result.append(word[:n]);word=word[n:]
            line=(line+' '+word).strip()
        result.append(line)
    if len(cache)>=512:cache.clear()
    cache[key]=tuple(result)
    return cache[key]


def paragraph(screen,surf,text,x,y,width,size=18,bold=False,color=None):
    font=face(screen,size,bold);height=font.get_linesize()+3
    for line in lines(screen,text,width,size,bold):
        surf.blit(font.render(line,True,color or ui.INK),(x,y));y+=height
    return y


def caption(screen,surf,text,rect,size=16,bold=False,color=None,center=False):
    image=screen.text(face(screen,size,bold),text,rect.width,color or ui.INK)
    surf.blit(image,image.get_rect(center=rect.center) if center else image.get_rect(midleft=(rect.x,rect.centery)))


def card(surf,rect):
    pygame.draw.rect(surf,ui.CARD,rect,border_radius=14)


def action_style(app,action_id):
    action=next(a for a in app['actions'] if a['id']==action_id)
    steps=action['steps'] if action['action']=='batch' else [action]
    destructive=any(s['action'] in ('clear','remove_checked') for s in steps)
    # A complete reset belongs below the main interaction, with secondary style.
    destructive=destructive or (len(steps)>1 and all(s['action']=='set' and s['value'] in ('',0,False,[]) for s in steps))
    values={key:f['value'] for key,f in fields(app).items()}
    ready=True
    for step in steps:
        if step['action']=='set':values[step['target']]=step['value']
        if step['action'] in ('append','append_record'):
            if not str(values[step['source']]).strip():ready=False
        if step['action']=='calculate' and step['operator']=='divide':
            right=step['right'];divisor=values[right['field']] if 'field' in right else right['literal']
            if divisor==0:ready=False
        if step['action']=='remove_checked' and not any(i['checked'] for i in values[step['target']]):ready=False
    return not destructive,ready


def control(screen,surf,rect,label,act,clip=None,primary=False,enabled=True,icon=None,**payload):
    if not enabled:
        pygame.draw.rect(surf,ui.CARD,rect,border_radius=12)
        if icon:draw_asset(surf,icon,(rect.x+28,rect.centery),22,ui.MUTED,ui.CARD)
        caption(screen,surf,label,pygame.Rect(rect.x+(48 if icon else 8),rect.y,rect.width-(56 if icon else 16),rect.height),17,True,ui.MUTED,True)
        return
    pygame.draw.rect(surf,ui.INK if primary else ui.BG,rect,border_radius=12)
    if not primary:pygame.draw.rect(surf,ui.MUTED,rect,1,border_radius=12)
    color=ui.BG if primary else ui.INK
    if label in ('‹','›','×','Edit'):
        cx,cy=rect.center
        if label=='×':
            pygame.draw.line(surf,color,(cx-6,cy-6),(cx+6,cy+6),2)
            pygame.draw.line(surf,color,(cx+6,cy-6),(cx-6,cy+6),2)
        elif label=='Edit':
            pygame.draw.line(surf,color,(cx-7,cy+6),(cx+5,cy-6),4)
            pygame.draw.lines(surf,color,False,[(cx-8,cy+3),(cx-9,cy+9),(cx-3,cy+8)],2)
        else:
            d=1 if label=='›' else -1
            pygame.draw.lines(surf,color,False,[(cx-d*4,cy-8),(cx+d*4,cy),(cx-d*4,cy+8)],2)
    else:
        if icon:draw_asset(surf,icon,(rect.x+28,rect.centery),22,color,ui.INK if primary else ui.BG)
        caption(screen,surf,label,pygame.Rect(rect.x+(48 if icon else 8),rect.y,rect.width-(56 if icon else 16),rect.height),17,True,color,True)
    screen.add(rect,act,clip=clip,**payload)


def number(value):return format(value,'.8g')


def component_heading(screen,surf,component,rect,size=15,color=None):
    icon=component_icon(component['type'],component.get('label',''),component.get('icon'))
    if icon:
        draw_asset(surf,icon,(rect.x+11,rect.centery),22,color or ui.MUTED,ui.CARD)
        rect=pygame.Rect(rect.x+32,rect.y,rect.width-32,rect.height)
    caption(screen,surf,component['label'],rect,size,color=color or ui.MUTED)


def render(screen,surf,app,layout,y,body,components=None):
    state=fields(app);margin=layout.get('margin',24);width=body.width-margin*2;x=body.x+margin
    timers=screen.component_timers
    for component in app['components'] if components is None else components:
        kind=component['type'];bind=component.get('bind');f=state.get(bind);value=f['value'] if f else None
        cid=component['id'];key=app['id']+':'+cid
        top=screen.cy(y,body)
        if kind=='illustration':
            size={'small':64,'medium':96,'large':144}[component['size']]
            h=size+52
            if pygame.Rect(x,top,width,h).colliderect(body):
                draw_asset(surf,component['icon'],(x+width//2,top+size//2+8),size,ui.INK,ui.BG)
                caption(screen,surf,component['label'],pygame.Rect(x,top+size+20,width,28),16,center=True)
            y+=h+GAP;continue
        if kind=='choice_game':
            from choice_game import render as render_game
            y+=render_game(screen,surf,app,component,x,top,width,body)+GAP
        elif kind in ('text','callout','hero_banner','accordion','summary_footer'):
            text=value if f else component['text'];bold=kind in ('hero_banner','summary_footer')
            size=22 if kind=='hero_banner' else 18
            icon=component.get('icon');inset=60 if icon else 0
            if kind=='accordion':
                title,detail=_split_kv(str(text));opened=key in screen.expanded_accordions
                h=64+(len(lines(screen,detail or text,width-32))*face(screen).get_linesize()+24 if opened else 0)
            else:h=max(76 if icon else 0,len(lines(screen,text,width-32-inset,size,bold))*(face(screen,size,bold).get_linesize()+3)+32)
            rect=pygame.Rect(x,top,width,h)
            if kind!='text':card(surf,rect)
            if icon:draw_asset(surf,icon,(x+36,top+36),40,ui.INK,ui.CARD if kind!='text' else ui.BG)
            if kind=='accordion':
                caption(screen,surf,title,pygame.Rect(x+16+inset,top+8,width-72-inset,48),18,True)
                caption(screen,surf,'−' if opened else '+',pygame.Rect(rect.right-52,top+8,36,48),22,center=True)
                screen.add(pygame.Rect(x,top,width,64),'component_accordion',clip=body,text=key)
                if opened:paragraph(screen,surf,detail or text,x+16,top+72,width-32)
            else:paragraph(screen,surf,text,x+16+inset,top+16,width-32-inset,size,bold)
            y+=h+GAP;continue
        if kind in ('button','confirm_button'):
            armed=kind=='confirm_button' and screen.armed_confirm==component['action']
            primary,enabled=action_style(app,component['action'])
            control(screen,surf,pygame.Rect(x,top,width,56),'Confirm '+component['label'] if armed else component['label'],
                    'component_confirm' if kind=='confirm_button' else 'component_action',body,primary,enabled=enabled,
                    icon=component_icon(kind,component['label'],component.get('icon')),text=component['action'])
            y+=56+GAP;continue
        if kind in ('input','number_input'):
            rect=pygame.Rect(x,top,width,88);card(surf,rect)
            component_heading(screen,surf,component,pygame.Rect(x+16,top+8,width-32,24),14)
            shown=number(value) if kind=='number_input' else (value or 'Tap to enter…')
            caption(screen,surf,shown,pygame.Rect(x+16,top+36,width-48,36),20)
            screen.add(rect,'component_number_input' if kind=='number_input' else 'component_input',clip=body,text=bind)
            y+=88+GAP;continue
        if kind=='toggle':
            rect=pygame.Rect(x,top,width,72);card(surf,rect)
            component_heading(screen,surf,component,pygame.Rect(x+16,top+12,width-112,48),18,ui.INK)
            track=pygame.Rect(rect.right-80,top+20,60,32)
            pygame.draw.rect(surf,ui.INK if value else ui.MUTED,track,border_radius=16)
            pygame.draw.circle(surf,ui.BG,(track.right-16 if value else track.left+16,track.centery),12)
            screen.add(rect,'component_toggle',clip=body,text=bind);y+=72+GAP;continue
        if f and f['type']=='number':
            preview=getattr(screen,'slider_preview',None)
            if preview and preview[:2]==(app['id'],bind):value=preview[2]
            goal=component.get('goal');val=number(value);unit=component.get('unit','')
            timer=kind=='timer';step=kind in ('stepper','tally_pad','unit_converter','quick_chips','randomizer','pacer')
            meter=goal is not None
            interactive_meter=kind in ('arc_gauge','bar_gauge','xy_pad')
            h=224 if interactive_meter else 192 if timer or kind=='unit_converter' else 160 if step or meter else 112
            rect=pygame.Rect(x,top,width,h)
            if not rect.colliderect(body):y+=h+GAP;continue
            card(surf,rect)
            component_heading(screen,surf,component,pygame.Rect(x+16,top+12,width-32,26))
            if timer:
                record=timers.get(app['id']+':'+bind,{})
                remaining=max(0,int(record['base']-(screen.time-record['started'])//1000)) if record.get('running') else max(0,int(value))
                minutes,seconds=divmod(remaining,60);val=f'{minutes:02d}:{seconds:02d}'
            if kind=='pacer':
                duration=max(1,float(value));phase=int(screen.time/(duration*1000))%4
                val=('Inhale','Hold','Exhale','Rest')[phase];unit=''
            display=val if timer else (unit+format(value,',.2f')) if unit in ('$', '€', '£') else (val+' '+unit).strip()
            caption(screen,surf,display,pygame.Rect(x+16,top+42,width-32,50),32,True)
            if kind=='unit_converter':
                conversions={'kg':('lb',value*2.20462262),'lb':('kg',value/2.20462262),
                             'c':('°F',value*9/5+32),'°c':('°F',value*9/5+32),
                             'f':('°C',(value-32)*5/9),'°f':('°C',(value-32)*5/9),
                             'km':('mi',value/1.609344),'mi':('km',value*1.609344),
                             'oz':('ml',value*29.5735296),'ml':('oz',value/29.5735296)}
                converted=conversions.get(unit.lower())
                extra='= '+number(converted[1])+' '+converted[0] if converted else 'Set a supported source unit'
                caption(screen,surf,extra,pygame.Rect(x+16,top+88,width-32,28),15,color=ui.MUTED)
                h=192;rect.height=h;card(surf,rect)
                component_heading(screen,surf,component,pygame.Rect(x+16,top+12,width-32,26))
                caption(screen,surf,val+' '+unit,pygame.Rect(x+16,top+42,width-32,50),32,True)
                caption(screen,surf,extra,pygame.Rect(x+16,top+88,width-32,28),15,color=ui.MUTED)
            if timer:
                w=(width-48)//2
                control(screen,surf,pygame.Rect(x+16,top+120,w,56),'Pause' if record.get('running') else 'Start',
                        'component_timer_toggle',body,True,text=bind)
                control(screen,surf,pygame.Rect(x+32+w,top+120,w,56),'Reset','component_timer_reset',body,text=bind)
            elif step:
                by=top+h-64
                if kind=='randomizer':control(screen,surf,pygame.Rect(x+16,by,width-32,48),'Roll again','component_random',body,True,text=bind)
                else:
                    w=(width-48)//2
                    control(screen,surf,pygame.Rect(x+16,by,w,48),'−  Decrease','component_step',body,text=bind,amount=-1)
                    control(screen,surf,pygame.Rect(x+32+w,by,w,48),'+  Increase','component_step',body,True,text=bind,amount=1)
            elif meter:
                ratio=max(0,min(1,(value-f['min'])/max(1e-9,goal-f['min'])))
                track=pygame.Rect(x+16,top+108,width-32,10)
                pygame.draw.rect(surf,ui.MUTED,track,border_radius=5)
                fill=track.copy();fill.width=round(track.width*ratio)
                if fill.width:pygame.draw.rect(surf,ui.INK,fill,border_radius=5)
                caption(screen,surf,number(goal)+' '+unit+' goal',pygame.Rect(x+16,top+125,width-32,24),14,color=ui.MUTED)
                if kind=='xy_pad':
                    slider=pygame.Rect(x+16,top+160,width-32,48)
                    caption(screen,surf,'Drag to adjust',slider,14,color=ui.MUTED,center=True)
                    pygame.draw.circle(surf,ui.INK,(round(slider.x+20+(slider.width-40)*ratio),slider.centery),10)
                    screen.add(slider,'component_xy',clip=body,text=bind,amount=goal)
                elif interactive_meter:
                    w=(width-48)//2
                    control(screen,surf,pygame.Rect(x+16,top+160,w,48),'−  Decrease','component_step',body,text=bind,amount=-1)
                    control(screen,surf,pygame.Rect(x+32+w,top+160,w,48),'+  Increase','component_step',body,True,text=bind,amount=1)
            y+=h+GAP;continue
        if f and f['type']=='items':
            icon=component_icon(kind,component['label'],component.get('icon'));inset=32 if icon else 0
            if icon:draw_asset(surf,icon,(x+11,top+12),22,ui.INK,ui.BG)
            y=paragraph(screen,surf,component['label'],x+inset,top,width-inset,16,True)-body.top+screen.scroll+12
            items=value
            if not items:
                rect=pygame.Rect(x,screen.cy(y,body),width,100);card(surf,rect)
                paragraph(screen,surf,'No entries yet. Use the form to add your first entry.',x+20,rect.y+20,width-40,color=ui.MUTED)
                y+=100+GAP;continue
            if kind in ('segmented','tabs','date_strip','phase_bar','tag_chips','habit_grid','matrix_2x2'):
                # Wrap options instead of squeezing an arbitrary list into one line.
                cols=2 if kind=='matrix_2x2' else min(3,len(items));w=(width-12*(cols-1))//cols
                for i,item in enumerate(items):
                    rect=pygame.Rect(x+(i%cols)*(w+12),screen.cy(y+(i//cols)*68,body),w,56)
                    control(screen,surf,rect,item['label'],'component_item' if kind in ('tag_chips','habit_grid') else 'component_radio',
                            body,item['checked'],icon=item.get('icon'),text=bind,index=i)
                y+=math.ceil(len(items)/cols)*68+4;continue
            if kind in ('stat_grid','bar_chart'):
                records=[]
                for item in items:
                    title,raw=_split_kv(item['label'])
                    try:amount=float(raw)
                    except ValueError:amount=None
                    records.append((title,raw,amount))
                if kind=='stat_grid':
                    w=(width-12)//2
                    for i,(title,raw,amount) in enumerate(records):
                        rect=pygame.Rect(x+(i%2)*(w+12),screen.cy(y+(i//2)*120,body),w,108);card(surf,rect)
                        label_rect=rect.inflate(-24,0).move(0,-24)
                        if items[i].get('icon'):
                            draw_asset(surf,items[i]['icon'],(rect.x+22,rect.y+30),20,ui.MUTED,ui.CARD)
                            label_rect.x+=28;label_rect.width-=28
                        caption(screen,surf,title,label_rect,14,color=ui.MUTED)
                        caption(screen,surf,raw or '—',rect.inflate(-24,0).move(0,16),26,True)
                    y+=math.ceil(len(records)/2)*120+4
                else:
                    maximum=max([abs(amount) for _,_,amount in records if amount is not None]+[1])
                    for index,(title,raw,amount) in enumerate(records):
                        rect=pygame.Rect(x,screen.cy(y,body),width,88);card(surf,rect)
                        inset=32 if items[index].get('icon') else 0
                        if inset:draw_asset(surf,items[index]['icon'],(x+27,rect.y+24),22,ui.INK,ui.CARD)
                        caption(screen,surf,title,pygame.Rect(x+16+inset,rect.y+8,width-120-inset,32),16)
                        caption(screen,surf,raw or '—',pygame.Rect(rect.right-96,rect.y+8,80,32),16,True)
                        track=pygame.Rect(x+16,rect.y+54,width-32,12)
                        pygame.draw.rect(surf,ui.MUTED,track,border_radius=6)
                        fill=track.copy();fill.width=round(track.width*abs(amount or 0)/maximum)
                        if fill.width:pygame.draw.rect(surf,ui.INK,fill,border_radius=6)
                        y+=100
                continue
            if kind=='deck_card':
                index=screen.deck_indices.get(key,0)%len(items);item=items[index]
                art_height=116 if item.get('icon') else 0
                height=max(164,len(lines(screen,item['label'],width-40,22))*face(screen,22).get_linesize()+96)+art_height
                rect=pygame.Rect(x,screen.cy(y,body),width,height);card(surf,rect)
                if art_height:draw_asset(surf,item['icon'],(rect.centerx,rect.y+64),96,ui.INK,ui.CARD)
                paragraph(screen,surf,item['label'],x+20,rect.y+20+art_height,width-40,22,True)
                caption(screen,surf,f'{index+1} / {len(items)}',pygame.Rect(x+76,rect.bottom-64,width-152,48),15,center=True)
                control(screen,surf,pygame.Rect(x+12,rect.bottom-64,56,48),'‹','component_deck_nav',body,text=key,amount=-1)
                control(screen,surf,pygame.Rect(rect.right-68,rect.bottom-64,56,48),'›','component_deck_nav',body,text=key,amount=1)
                y+=height+GAP;continue
            if kind=='inventory_list':
                for i,item in enumerate(items):
                    name,qty=_item_qty(item['label']);rect=pygame.Rect(x,screen.cy(y,body),width,88);card(surf,rect)
                    inset=32 if item.get('icon') else 0
                    if inset:draw_asset(surf,item['icon'],(x+27,rect.y+24),22,ui.INK,ui.CARD)
                    caption(screen,surf,name,pygame.Rect(x+16+inset,rect.y+8,width-144-inset,32),17,True)
                    caption(screen,surf,'Quantity: '+str(qty),pygame.Rect(x+16,rect.y+42,width-144,28),15,color=ui.MUTED)
                    for offset,label,amount in ((112,'−',-1),(56,'+',1)):
                        control(screen,surf,pygame.Rect(rect.right-offset,rect.centery-24,48,48),label,'component_item_qty',body,text=bind,index=i,amount=amount)
                    y+=100
                continue
            for i,item in enumerate(items):
                label=item['label'];editable=kind in ('list','inventory_list','key_value_log','data_table')
                # Every row wraps to its content and reserves separate 48px edit/remove targets.
                icon_inset=28 if item.get('icon') else 0
                text_width=width-(184 if editable else 88)-icon_inset
                h=max(76,len(lines(screen,label,text_width,17))*face(screen,17).get_linesize()+32)
                rect=pygame.Rect(x,screen.cy(y,body),width,h)
                if not rect.colliderect(body):y+=h+8;continue
                card(surf,rect)
                box=pygame.Rect(x+12,rect.y+(h-48)//2,48,48)
                check=box.inflate(-24,-24)
                pygame.draw.rect(surf,ui.INK,check,0 if item['checked'] else 2,border_radius=5)
                if item['checked']:
                    pygame.draw.lines(surf,ui.BG,False,[(check.x+5,check.centery),(check.centerx,check.bottom-6),(check.right-4,check.y+6)],2)
                screen.add(box,'component_item',clip=body,text=bind,index=i)
                if icon_inset:draw_asset(surf,item['icon'],(x+78,rect.y+28),22,ui.MUTED if item['checked'] else ui.INK,ui.CARD)
                paragraph(screen,surf,label,x+68+icon_inset,rect.y+16,text_width,17,color=ui.MUTED if item['checked'] else ui.INK)
                if editable:
                    control(screen,surf,pygame.Rect(rect.right-112,rect.centery-24,48,48),'Edit','component_item_edit',body,text=bind,index=i)
                    control(screen,surf,pygame.Rect(rect.right-56,rect.centery-24,48,48),'×','component_item_remove',body,text=bind,index=i)
                y+=h+8
            y+=8
    return y
