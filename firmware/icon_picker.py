"""Search and select an offline app logo, using the same touch path as apps."""
import math
from functools import lru_cache
import pygame
import phone as ui
from contract.asset_catalog import search,app_icon,for_prompt
from icon_assets import draw

PAGE_SIZE=30

@lru_cache(maxsize=64)
def choices(query,context):
    if query:return search(query)
    preferred=[context.split()[0]]+[entry['id'] for entry in for_prompt(context)['icons']]
    return list(dict.fromkeys(preferred+search()))


def render(screen,surf,device):
    from components import control,caption
    picker=screen.asset_picker;app=device.find(picker['app_id'])
    if app is None:screen.asset_picker=None;return
    surf.fill(screen.bg);screen.hits.clear()
    screen.label(surf,'App icon',(24,62),28,align='left',width=340)
    control(screen,surf,pygame.Rect(400,28,56,56),'‹','asset_close')
    control(screen,surf,pygame.Rect(24,112,432,56),picker['query'] or 'Search icons…',
            'asset_search',icon='search')
    context=app_icon(app)+' '+app.get('title','')
    names=choices(picker['query'],context);pages=max(1,math.ceil(len(names)/PAGE_SIZE))
    picker['page']=max(0,min(pages-1,picker['page']))
    screen.label(surf,f'{len(names):,} icons',(24,192),12,align='left',width=432,color=ui.MUTED)
    selected=app_icon(app)
    for index,name in enumerate(names[picker['page']*PAGE_SIZE:(picker['page']+1)*PAGE_SIZE]):
        rect=pygame.Rect(24+(index%5)*88,216+(index//5)*82,80,76)
        active=name==selected
        bg=ui.INK if active else ui.CARD;color=ui.BG if active else ui.INK
        pygame.draw.rect(surf,bg,rect,border_radius=12)
        draw(surf,name,(rect.centerx,rect.y+26),36,color,bg)
        caption(screen,surf,name.replace('-',' '),pygame.Rect(rect.x+4,rect.bottom-22,72,18),11,color=color,center=True)
        screen.add(rect,'asset_select',text=name)
    if not names:screen.label(surf,'No matching icons. Try another word.',(240,350),16,width=420)
    control(screen,surf,pygame.Rect(24,736,56,48),'‹','asset_page',enabled=picker['page']>0,amount=-1)
    control(screen,surf,pygame.Rect(92,736,96,48),'Auto','asset_auto')
    screen.label(surf,f"{picker['page']+1} / {pages}",(286,760),16,width=180)
    control(screen,surf,pygame.Rect(400,736,56,48),'›','asset_page',enabled=picker['page']<pages-1,amount=1)
