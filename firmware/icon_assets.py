"""Offline PNG masks, loaded on demand and recolored with bounded caches."""
from functools import lru_cache
import io
import zipfile
import pygame
from contract.asset_catalog import ROOT,resolve
from game_art import gesture

CUSTOM={'rps-rock':'rock','rps-paper':'paper','rps-scissors':'scissors',
        'element-flame':'flame','element-water':'water','element-leaf':'leaf'}
SPORTS={'basketball','soccer-ball','baseball','tennis-ball','eight-ball','person-running'}


@lru_cache(maxsize=1)
def archive():return zipfile.ZipFile(ROOT/'icons.zip')


@lru_cache(maxsize=96)
def mask(name):return pygame.image.load(io.BytesIO(archive().read(name+'.png')),name+'.png')


@lru_cache(maxsize=192)
def _image(name,size,color,background):
    if name in CUSTOM:return gesture(CUSTOM[name],size,color,background)
    if name in SPORTS:
        from sport_art import image as sport_image
        return sport_image(name,size,color,background)
    image=pygame.transform.smoothscale(mask(name),(size,size))
    image.fill((*color[:3],255),special_flags=pygame.BLEND_RGBA_MULT)
    return image


def image(name,size,color,background=(0,0,0)):
    canonical=resolve(name)
    if canonical is None:raise ValueError('Unknown offline asset: '+str(name))
    return _image(canonical,max(8,min(192,round(size))),tuple(color[:3]),tuple(background[:3]))


def draw(surf,name,center,size,color,background=(0,0,0)):
    art=image(name,size,color,background);surf.blit(art,art.get_rect(center=center))
