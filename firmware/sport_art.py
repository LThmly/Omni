"""Original vector marks for common sports missing from the base icon pack."""
from functools import lru_cache
import math
import pygame


@lru_cache(maxsize=96)
def image(name,size,color,background):
    surface=pygame.Surface((size*2,size*2),pygame.SRCALPHA);s=size*2/100
    def p(x,y):return round(x*s),round(y*s)
    def line(points,width=5):pygame.draw.lines(surface,color,False,[p(*point) for point in points],max(1,round(width*s)))
    def circle(center,radius,width=0,ink=color):pygame.draw.circle(surface,ink,p(*center),round(radius*s),round(width*s))
    def arc(rect,start,end,width=5):pygame.draw.arc(surface,color,pygame.Rect(*(round(v*s) for v in rect)),start,end,max(1,round(width*s)))
    if name=='person-running':
        circle((63,16),8)
        for points in ([(54,32),(41,48),(65,63),(53,86)],[(43,49),(28,72),(12,72)],
                       [(52,33),(72,43),(88,32)],[(51,34),(30,28),(19,39)]):
            line(points,7)
    else:
        circle((50,50),39,5)
        if name=='basketball':
            line([(12,50),(88,50)]);line([(50,12),(50,88)])
            arc((-21,9,68,82),-1.1,1.1);arc((53,9,68,82),math.pi-1.1,math.pi+1.1)
        elif name=='soccer-ball':
            points=[p(50+14*math.cos(-math.pi/2+i*math.tau/5),50+14*math.sin(-math.pi/2+i*math.tau/5)) for i in range(5)]
            pygame.draw.polygon(surface,color,points)
            for i in range(5):
                a=-math.pi/2+i*math.tau/5
                line([(50+14*math.cos(a),50+14*math.sin(a)),(50+32*math.cos(a),50+32*math.sin(a))])
                b1=a-.2;b2=a+.2
                pygame.draw.polygon(surface,color,[p(50+31*math.cos(a),50+31*math.sin(a)),p(50+38*math.cos(b1),50+38*math.sin(b1)),p(50+38*math.cos(b2),50+38*math.sin(b2))])
        elif name in ('baseball','tennis-ball'):
            arc((-30,13,77,74),-1.15,1.15);arc((53,13,77,74),math.pi-1.15,math.pi+1.15)
            if name=='baseball':
                for y,x in ((25,37),(37,42),(50,44),(63,42),(75,37)):
                    line([(x-4,y-3),(x+4,y+3)],2);line([(96-x,y+3),(104-x,y-3)],2)
        else: # eight-ball
            circle((50,50),38,ink=color);circle((50,47),19,ink=background)
            circle((50,41),6,2);circle((50,53),6,2)
    return pygame.transform.smoothscale(surface,(size,size))
