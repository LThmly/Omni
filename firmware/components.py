"""Fixed pygame component renderer. Layout and event behavior belong to the device."""
import pygame
import phone as ui
from contract.runtime import fields


def render(screen,surf,app,layout,y,body):
    state=fields(app);margin=layout['margin'];width=ui.PW-margin*2
    for component in app['components']:
        kind=component['type'];field=state.get(component.get('bind'));value=field['value'] if field else None
        if kind=='text':
            text=value if field else component['text']
            image=screen.text(screen.font(20),text,width,ui.INK)
            surf.blit(image,(margin,screen.cy(y,body)));y+=image.get_height()+14
        elif kind in ('number','progress'):
            caption=screen.font(17).render(component['label'],True,ui.MUTED)
            surf.blit(caption,(margin,screen.cy(y,body)));y+=28
            number=screen.text(screen.font(36,bold=True),str(value)+' '+component['unit'],width,ui.INK)
            surf.blit(number,(margin,screen.cy(y,body)));y+=number.get_height()+12
            if kind=='progress':
                track=pygame.Rect(margin,screen.cy(y,body),width,16)
                pygame.draw.rect(surf,ui.CARD,track,border_radius=8)
                fill=track.copy();fill.width=round(width*max(0,min(1,value/component['goal'])))
                if fill.width:pygame.draw.rect(surf,ui.INK,fill,border_radius=8)
                y+=30
        elif kind=='list':
            caption=screen.font(17).render(component['label'],True,ui.MUTED)
            surf.blit(caption,(margin,screen.cy(y,body)));y+=30
            for index,item in enumerate(value):
                rect=pygame.Rect(margin,screen.cy(y,body),width,56)
                pygame.draw.rect(surf,ui.CARD,rect,border_radius=10)
                box=pygame.Rect(rect.x+12,rect.y+17,22,22)
                pygame.draw.rect(surf,ui.INK,box,0 if item['checked'] else 2,border_radius=4)
                label=screen.text(screen.font(18),item['label'],width-58,ui.MUTED if item['checked'] else ui.INK)
                surf.blit(label,label.get_rect(midleft=(rect.x+48,rect.centery)))
                screen.add(rect,'component_item',clip=body,text=component['bind'],index=index)
                y+=64
            if not value:
                label=screen.font(18).render('No items yet',True,ui.MUTED)
                surf.blit(label,(margin,screen.cy(y,body)));y+=34
        else:
            rect=pygame.Rect(margin,screen.cy(y,body),width,64 if kind=='input' else 56)
            pygame.draw.rect(surf,ui.CARD,rect,border_radius=10)
            if kind=='button':
                label=screen.text(screen.font(19,bold=True),component['label'],width-24,ui.INK)
                surf.blit(label,label.get_rect(center=rect.center))
                screen.add(rect,'component_action',clip=body,text=component['action'])
            elif kind=='toggle':
                label=screen.text(screen.font(18),component['label'],width-90,ui.INK)
                surf.blit(label,label.get_rect(midleft=(rect.x+12,rect.centery)))
                track=pygame.Rect(rect.right-64,rect.y+14,48,28)
                pygame.draw.rect(surf,ui.INK,track,2,border_radius=14)
                pygame.draw.circle(surf,ui.INK,(track.right-14 if value else track.left+14,track.centery),8)
                screen.add(rect,'component_toggle',clip=body,text=component['bind'])
            elif kind=='input':
                label=screen.text(screen.font(17),value[-80:] or component['label'],width-24,ui.INK if value else ui.MUTED)
                surf.blit(label,label.get_rect(midleft=(rect.x+12,rect.centery)))
                screen.add(rect,'component_input',clip=body,text=component['bind'])
            y+=rect.height+12
    return y
