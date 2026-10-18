#!/usr/bin/env python3
"""Rebuild the pinned, licensed offline icon pack. No runtime SVG dependency."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import urllib.request
import zipfile

VERSION='1.59.0'
URL=f'https://registry.npmjs.org/lucide-static/-/lucide-static-{VERSION}.tgz'
SHA256='39e2f835692c193233ac7bcdf34eb0cc2da0f839fd9f3674c34d2751bccf37f0'
ROOT=Path(__file__).resolve().parents[1]/'assets/icons'
CUSTOM={
    'rps-rock':['rock','fist','hand','game','rock paper scissors'],
    'rps-paper':['paper','hand','palm','game','rock paper scissors'],
    'rps-scissors':['scissors','hand','game','rock paper scissors'],
    'element-flame':['fire','flame','element','game'],
    'element-water':['water','drop','element','game'],
    'element-leaf':['leaf','nature','element','game'],
    'basketball':['ball','basketball','sport','court','team'],
    'soccer-ball':['ball','soccer','football','sport','goal','team'],
    'baseball':['ball','baseball','sport','bat','team'],
    'tennis-ball':['ball','tennis','sport','racket'],
    'eight-ball':['ball','pool','billiards','game','eight'],
    'person-running':['person','running','runner','jog','fitness','workout','sport'],
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,help='Use an already-downloaded pinned npm archive')
    args=parser.parse_args()
    data=args.archive.read_bytes() if args.archive else urllib.request.urlopen(URL,timeout=60).read()
    if hashlib.sha256(data).hexdigest()!=SHA256:raise SystemExit('Icon archive checksum mismatch')
    import pygame
    icons={};aliases={};signatures={};pack=io.BytesIO();ROOT.mkdir(parents=True,exist_ok=True)
    def signature(svg):
        return re.sub(r'\s+',' ',re.sub(r'\sclass="[^"]*"','',re.sub(r'<!--.*?-->','',svg,flags=re.S))).strip()
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as source,zipfile.ZipFile(pack,'w',compression=zipfile.ZIP_STORED) as output:
        nodes=json.load(source.extractfile('package/icon-nodes.json'))
        tags=json.load(source.extractfile('package/tags.json'))
        for name in sorted(nodes):
            if not re.fullmatch(r'[a-z][a-z0-9-]*',name):raise ValueError('Invalid icon name')
            svg=source.extractfile(f'package/icons/{name}.svg').read().decode()
            signatures[signature(svg)]=name
            svg=re.sub(r'width="24"','width="144"',svg,count=1)
            svg=re.sub(r'height="24"','height="144"',svg,count=1).replace('currentColor','#ffffff')
            image=pygame.image.load(io.BytesIO(svg.encode()),name+'.svg')
            if image.get_size()!=(144,144) or image.get_bounding_rect().width<1:raise ValueError('Empty icon: '+name)
            png=io.BytesIO();pygame.image.save(image,png,'icon.png')
            entry=zipfile.ZipInfo(name+'.png',date_time=(1980,1,1,0,0,0));output.writestr(entry,png.getvalue())
            icons[name]={'tags':tags.get(name,[]),'source':'lucide'}
        license_text=source.extractfile('package/LICENSE').read()
        for member in source.getmembers():
            if member.name.startswith('package/icons/') and member.name.endswith('.svg'):
                name=Path(member.name).stem
                if name not in icons:
                    target=signatures.get(signature(source.extractfile(member).read().decode()))
                    if target:aliases[name]=target
    for name,tags in CUSTOM.items():icons[name]={'tags':tags,'source':'omni'}
    aliases.update({k:v for k,v in {'ball':'basketball','person':'person-standing','people':'users',
        'soccer':'soccer-ball','football':'soccer-ball','running':'person-running','fitness':'dumbbell',
        'rock':'rps-rock','paper':'rps-paper','water':'element-water'}.items() if v in icons})
    manifest={'version':VERSION,'source':URL,'source_sha256':SHA256,'raster_size':144,
              'count':len(icons),'aliases':aliases,'icons':icons}
    (ROOT/'catalog.json').write_text(json.dumps(manifest,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n')
    (ROOT/'icons.zip').write_bytes(pack.getvalue());(ROOT/'LICENSE-LUCIDE.txt').write_bytes(license_text)
    print(f'Built {len(icons)} assets ({len(nodes)} Lucide + {len(CUSTOM)} Omni); packed PNGs: {len(pack.getvalue()):,} bytes')


if __name__=='__main__':main()
