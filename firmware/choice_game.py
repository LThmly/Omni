"""Native layout and reveal animation for declarative choice-versus-choice games."""
import math
import pygame
import phone as ui
from contract.runtime import fields
from game_art import gesture
from icon_assets import image

REVEAL_MS=620

def artwork(icon,size,color,background):
    return gesture(icon,size,color,background) if icon in ('rock','paper','scissors','flame','water','leaf') else image(icon,size,color,background)


def render(screen,surf,app,component,x,y,width,body):
    from components import caption,card
    state=fields(app);key=app['id']+':'+component['id']
    round_state=screen.choice_rounds.get(key)
    elapsed=screen.time-round_state['started'] if round_state else REVEAL_MS
    waiting=screen.prefs['motion'] and elapsed<REVEAL_MS
    shown=round_state['before'] if waiting else {k:f['value'] for k,f in state.items()}
    outcome='' if waiting else shown[component['bind']]
    choices=component['choices'];lookup={c['id']:c for c in choices}
    def text(value,box,size=16,bold=False,color=None):
        caption(screen,surf,value,pygame.Rect(x+box[0],y+box[1],box[2],box[3]),size,bold,color,True)
    # One quiet score strip, rather than three independently editable widgets.
    strip=pygame.Rect(x,y,width,64);card(surf,strip)
    for i,(label,binding) in enumerate((('YOU','wins'),('DRAWS','draws'),('OMNI','losses'))):
        col=width//3
        text(label,(i*col,7,col,17),11,color=ui.MUTED)
        text(str(shown[component[binding]]),(i*col,28,col,30),24,True)
    titles={'win':'You win.','loss':'Omni wins.','draw':"It’s a draw."}
    text('Rock. Paper. Scissors.' if waiting and set(lookup)=={'rock','paper','scissors'} else
         'Ready…' if waiting else titles.get(outcome,'Make your move.'),(0,84,width,44),28,True)
    player=shown[component['player']];opponent=shown[component['opponent']]
    detail='Tap a move to play a round'
    if outcome=='draw':detail='Same move. Go again.'
    elif outcome in ('win','loss') and player in lookup and opponent in lookup:
        winner,loser=(player,opponent) if outcome=='win' else (opponent,player)
        verb={('rock','scissors'):'blunts',('paper','rock'):'covers',('scissors','paper'):'cuts'}.get((winner,loser),'beats')
        detail=f"{lookup[winner]['label']} {verb} {lookup[loser]['label'].lower()}"
    text('Revealing your opponent' if waiting else detail,(0,132,width,28),15,color=ui.MUTED)
    gap=40;tile_width=(width-gap)//2
    for index,(name,move) in enumerate((('YOU',player),('OMNI',opponent))):
        tile=pygame.Rect(x+index*(tile_width+gap),y+180,tile_width,184)
        won=(outcome=='win' and index==0) or (outcome=='loss' and index==1)
        pygame.draw.rect(surf,ui.CARD,tile,border_radius=22)
        if won:pygame.draw.rect(surf,ui.INK,tile,2,border_radius=22)
        caption(screen,surf,name,pygame.Rect(tile.x,tile.y+12,tile.width,20),11,True,ui.MUTED,True)
        if waiting:
            icon='rock';offset=round(math.sin(max(0,elapsed)/REVEAL_MS*math.pi*6)*7)
        else:icon=lookup.get(move,{}).get('icon');offset=0
        if icon:
            size=min(112,tile.width-32);art=artwork(icon,size,ui.INK,ui.CARD)
            surf.blit(art,art.get_rect(center=(tile.centerx,tile.y+91+offset)))
        else:
            caption(screen,surf,'?',pygame.Rect(tile.x,tile.y+49,tile.width,80),48,False,ui.MUTED,True)
        caption(screen,surf,'…' if waiting else lookup.get(move,{}).get('label','Your pick' if index==0 else 'Hidden'),
                pygame.Rect(tile.x,tile.bottom-36,tile.width,24),14,True,center=True)
    text('VS',(tile_width,246,gap,28),12,True,color=ui.MUTED)
    text('CHOOSE YOUR MOVE' if not outcome else 'PLAY ANOTHER ROUND',(0,378,width,24),11,True,color=ui.MUTED)
    columns=min(3,len(choices));rows=math.ceil(len(choices)/columns)
    gap=10;button_width=(width-gap*(columns-1))//columns
    for i,choice in enumerate(choices):
        tile=pygame.Rect(x+(i%columns)*(button_width+gap),y+410+(i//columns)*116,button_width,104)
        selected=not waiting and player==choice['id']
        color=ui.BG if selected else ui.INK;bg=ui.INK if selected else ui.BG
        pygame.draw.rect(surf,bg,tile,border_radius=16)
        if not selected:pygame.draw.rect(surf,ui.MUTED,tile,1,border_radius=16)
        art=artwork(choice['icon'],60,color,bg)
        surf.blit(art,art.get_rect(center=(tile.centerx,tile.y+37)))
        caption(screen,surf,choice['label'],pygame.Rect(tile.x,tile.bottom-32,tile.width,24),14,True,color,True)
        if not waiting:screen.add(tile,'component_game',clip=body,text=component['id'],index=i)
    return 530+116*(rows-1)
