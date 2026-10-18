"""Shared offline asset names/search. Cloud and validation need no graphics code."""
from functools import lru_cache
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]/'assets/icons'


@lru_cache(maxsize=1)
def catalog():return json.loads((ROOT/'catalog.json').read_text())


def resolve(name):
    data=catalog();canonical=data['aliases'].get(name,name)
    return canonical if canonical in data['icons'] else None


def words(text):return set(re.findall(r'[a-z0-9]+',str(text).lower()))


@lru_cache(maxsize=1)
def index():
    return {name:(words(name),words(' '.join(info['tags']))) for name,info in catalog()['icons'].items()}


@lru_cache(maxsize=128)
def search(query='',limit=None):
    query=str(query).strip().lower();terms=words(query)
    if not terms:result=sorted(index())
    else:
        alias=resolve(query)
        ranked=[]
        for name,(names,tags) in index().items():
            matches=terms & (names|tags)
            if not matches and name!=alias:continue
            score=100*(name==alias)+12*len(terms&names)+4*len(terms&tags)+20*(query in name)
            ranked.append((-score,len(name),name))
        result=[name for _,_,name in sorted(ranked)]
    return result if limit is None else result[:limit]


def for_prompt(text):
    # A ranked short list keeps a large library out of every response schema.
    noise=words('create build make an a the app application with for and or to my me your personal '
                'called named include use meaningful specific clear keep it useful compact '
                'counter tracker track tracking count add edit remove reset buttons button '
                'page pages goal completed toward icon icons logo artwork illustration illustrations')
    terms=words(text)-noise
    preferred=search(' '.join(sorted(t for t in terms if not t.isdigit())),48) if terms else []
    common=['sparkles','notebook-pen','calendar-days','timer','dumbbell','wallet','heart',
            'book-open','list-checks','utensils','volleyball','person-standing','target',
            'chart-no-axes-combined','leaf','music','map-pin','trophy','rps-rock','rps-paper','rps-scissors']
    selected=list(dict.fromkeys(preferred+[resolve(n) for n in common if resolve(n)]))[:64]
    return {'total_assets':catalog()['count'],'suggested_app_icons':preferred[:8],
            'icons':[{'id':name,'tags':catalog()['icons'][name]['tags'][:5]} for name in selected]}


def app_icon(app):
    explicit=resolve(app.get('icon',''))
    if explicit:return explicit
    types={c['type'] for c in app.get('components',[])}
    text=app.get('title','')
    if 'choice_game' in types:return 'rps-scissors'
    suggestions=search(text,1)
    if suggestions:return suggestions[0]
    return 'list-checks' if 'list' in types else 'timer' if 'timer' in types else 'layout-grid'


@lru_cache(maxsize=512)
def component_icon(kind,label='',explicit=None):
    if explicit:return resolve(explicit)
    defaults={'number':'chart-column','number_input':'hash','timer':'timer','pacer':'wind',
              'input':'square-pen','toggle':'sliders-horizontal','progress':'target',
              'list':'list-checks','key_value_log':'notebook-pen','inventory_list':'package',
              'deck_card':'layers','stat_grid':'chart-column','bar_chart':'chart-column'}
    if kind in ('button','confirm_button'):
        terms=words(label)
        return 'rotate-ccw' if terms & {'reset','match','restart'} else 'trash-2' if terms & {'remove','delete','clear'} else 'plus' if terms & {'add','save','log'} else 'arrow-right'
    return resolve(defaults.get(kind,''))
