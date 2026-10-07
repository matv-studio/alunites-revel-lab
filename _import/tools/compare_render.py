#!/usr/bin/env python3
"""Compare le texte reconstruit depuis le WXR avec le texte réellement affiché sur alunites.com (extraction navigateur)."""
import json, sys, html, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from wxr_parse import text_only
R = Path(__file__).resolve().parent.parent
c = json.loads((R/'data/content.json').read_text())
raw = {}
for f in sorted((R/'raw').glob('projects-*.json')) + sorted((R/'raw').glob('posts-*.json')):
    for it in json.loads(f.read_text()): raw[it['slug']] = it
def norm(s): return re.sub(r'\s+',' ', html.unescape(s or '').replace(' ',' ')).strip()
issues = 0; checked = 0
for kind in ('projects','articles'):
    for p in c[kind]:
        if p['status'] != 'publish': continue
        r = raw.get(p['slug'])
        if not r: print('ABSENT du rendu:', p['slug']); issues += 1; continue
        checked += 1
        rb = r['blocks']; wb = p['blocks']
        if len(rb) != len(wb):
            print(f"{p['slug']}: nb blocs WXR={len(wb)} rendu={len(rb)}"); issues += 1
        for i,(a,b) in enumerate(zip(wb, rb)):
            if a['type'] != b['type']:
                print(f"{p['slug']} bloc {i}: type {a['type']} vs {b['type']}"); issues += 1; continue
            if a['type']=='text':
                ta, tb = text_only(a['body']), text_only(b.get('html',''))
            elif a['type']=='quote':
                ta, tb = text_only(a['quote'])+' '+text_only(a['author']), text_only(b.get('quote',''))+' '+norm(b.get('author',''))
            elif a['type'] in ('image','slider'):
                ia = [re.sub(r'-scaled$','',x['src'].split('/')[-1].rsplit('.',1)[0]) for x in ([a['image']] if a['type']=='image' else a['images']) if x]
                ib = [re.sub(r'-(\d+x\d+|scaled)$','', (x if isinstance(x,str) else x[0]).split('/')[-1].rsplit('.',1)[0]) for x in b.get('images',[])]
                ta, tb = ' '.join(ia), ' '.join(ib)
            elif a['type']=='video':
                ta, tb = a.get('vimeo') or '', ' '.join(b.get('vimeo',[]))
            else: continue
            if norm(ta) != norm(tb):
                issues += 1
                print(f"--- {p['slug']} bloc {i} ({a['type']})\n  WXR : {norm(ta)[:300]}\n  SITE: {norm(tb)[:300]}")
        h = r['header']
        for fld, wx, site in (('chapeau', text_only(p['chapeau']), text_only(h.get('chapeau') or '')), ('intro', text_only(p['intro']), text_only(h.get('text') or '')), ('hook', ' '.join(p['hook']), ' '.join(h.get('hook') or [])), ('keywords', ' | '.join(p['keywords']), ' | '.join(k for k in (h.get('keywords') or []) if k)), ('client', p['client'] if kind=='projects' else '', h.get('client') or '' if kind=='projects' else '')):
            if norm(wx) != norm(site):
                issues += 1; print(f"--- {p['slug']} header.{fld}\n  WXR : {norm(wx)[:300]}\n  SITE: {norm(site)[:300]}")
print(f"vérifiés={checked} écarts={issues}")
