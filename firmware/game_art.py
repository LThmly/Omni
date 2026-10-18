"""Small cached vector illustrations for native choice games, in either theme."""
from functools import lru_cache
import pygame


@lru_cache(maxsize=128)
def gesture(icon,size,ink,paper):
    # Draw at 2x for smooth edges, once per icon/size/palette, not per frame.
    scale=size*2/160
    surface=pygame.Surface((size*2,size*2),pygame.SRCALPHA)
    def point(p):return tuple(round(v*scale) for v in p)
    def rect(box,radius=8,color=ink):
        pygame.draw.rect(surface,color,pygame.Rect(*(round(v*scale) for v in box)),border_radius=round(radius*scale))
    def polygon(points,color=ink):pygame.draw.polygon(surface,color,[point(p) for p in points])
    def line(points,width=3,color=paper):pygame.draw.lines(surface,color,False,[point(p) for p in points],max(1,round(width*scale)))
    def finger(start,end,width):
        a,b=point(start),point(end);w=round(width*scale)
        pygame.draw.line(surface,ink,a,b,w)
        for p in (a,b):pygame.draw.circle(surface,ink,p,w//2)
    if icon=='rock':
        rect((35,49,98,78),22)
        for x,y in ((36,36),(61,28),(86,32),(111,42)):
            rect((x,y,24,58),10)
        rect((51,111,65,32),5)
        polygon([(28,76),(41,67),(76,83),(84,107),(63,120),(36,106)])
        line([(41,78),(65,87),(76,104)],4)
        for x,y in ((60,48),(85,42),(110,52)):line([(x,y),(x,y+27)],3)
        line([(76,120),(111,120)],3)
    elif icon=='paper':
        rect((44,65,83,67),25)
        for a,b,w in (((49,80),(46,35),17),((69,75),(68,20),18),
                      ((91,74),(92,17),18),((113,80),(116,32),17)):
            finger(a,b,w)
        finger((53,111),(26,79),21)
        rect((61,119,51,27),5)
        line([(63,95),(77,90),(99,93)],3)
        line([(64,109),(78,105),(101,108)],3)
    elif icon=='scissors':
        finger((72,85),(52,21),23)
        finger((94,80),(110,18),23)
        rect((43,76,84,56),20)
        rect((57,119,54,27),5)
        rect((91,66,27,43),11)
        polygon([(35,85),(46,77),(80,95),(78,118),(58,123),(39,110)])
        line([(47,88),(70,100),(73,112)],4)
        line([(93,79),(94,98),(110,103)],3)
    elif icon=='water':
        polygon([(80,14),(39,76),(32,101),(42,128),(64,143),(95,143),(119,124),(126,98),(114,71)])
        line([(48,103),(54,120),(68,126)],5)
    elif icon=='leaf':
        polygon([(136,22),(82,24),(43,42),(27,71),(29,107),(52,129),(86,123),(112,97),(128,60)])
        line([(40,120),(108,54)],5)
        line([(67,94),(63,62)],4);line([(83,79),(111,83)],4)
        finger((42,119),(23,141),7)
    else: # flame
        polygon([(91,12),(86,49),(112,33),(137,83),(132,117),(110,140),(66,147),(30,125),(23,89),(47,45),(52,85)])
        polygon([(80,77),(62,110),(69,131),(88,135),(103,119),(99,101),(91,111)],paper)
    return pygame.transform.smoothscale(surface,(size,size))
