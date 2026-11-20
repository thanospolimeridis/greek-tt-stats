#!/usr/bin/env python3
"""Build a portable static page without network access or JS dependencies."""
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def partition_results(data, dist):
    """Build static route files; shared rows are copied, never inferred or aggregated."""
    from collections import defaultdict
    groups = {kind:defaultdict(lambda: {'matches':[], 'doubles':[], 'fixtures':[]})
              for kind in ('event','player','club')}
    for kind in ('matches','doubles','fixtures'):
        for row in data.get(kind,[]):
            groups['event'][row['event_id']][kind].append(row)
            if kind == 'matches':
                for ident in (row['player1_id'], row['player2_id']):
                    groups['player'][ident][kind].append(row)
            elif kind == 'doubles':
                for field in ('player1_id','partner1_id','player2_id','partner2_id'):
                    if row.get(field):groups['player'][row[field]][kind].append(row)
            else:
                for ident in (row['home_club_id'], row['away_club_id']):
                    groups['club'][ident][kind].append(row)
    folder=dist/'records';folder.mkdir(exist_ok=True)
    paths={kind:{} for kind in groups}
    for kind, entries in groups.items():
        for ident, records in sorted(entries.items()):
            body=json.dumps(records,ensure_ascii=False,separators=(',',':'))+'\n'
            name=kind+'-'+hashlib.sha256(body.encode()).hexdigest()[:24]+'.json'
            (folder/name).write_text(body,encoding='utf-8')
            paths[kind][ident]='records/'+name
    return paths


def build_site(root=ROOT):
    data = json.loads((root/'data'/'catalog.json').read_text(encoding='utf-8'))
    provenance=data.get('meta',{}).get('provenance',{})
    # Keep the detailed audit downloadable without parsing every request in the UI.
    if provenance:
        data['meta']['provenance']={k:v for k,v in provenance.items() if k!='requests'}
    css = (root/'src'/'style.css').read_text(encoding='utf-8')
    js = (root/'src'/'app.js').read_text(encoding='utf-8')
    template = (root/'src'/'template.html').read_text(encoding='utf-8')
    import re
    def render(payload):
        # Source text cannot close the JSON element; template markers in data stay literal.
        serialized=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
        replacements={'/*INLINE_CSS*/':css,'/*INLINE_JS*/':js,'/*INLINE_JSON*/':serialized}
        return re.sub(r'/\*INLINE_(?:CSS|JS|JSON)\*/',lambda m:replacements[m[0]],template)
    html=render(data)
    dist = root/'dist'
    dist.mkdir(exist_ok=True)
    hosted={**data,'matches':[],'doubles':[],'fixtures':[],'meta':dict(data.get('meta',{}))}
    hosted['meta']['partitions']=partition_results(data,dist)
    hosted['meta']['table_counts']={kind:len(data.get(kind,[])) for kind in ('matches','doubles','fixtures')}
    from collections import Counter
    hosted['meta']['event_match_counts']=dict(Counter(m['event_id'] for m in data.get('matches',[]) if m['status']=='completed'))
    hosted['meta']['release_id']=hashlib.sha256(html.encode()).hexdigest()
    hosted_html=render(hosted)
    marker=dist/'version.json.tmp'
    marker.write_text(json.dumps({'release_id':hosted['meta']['release_id'],
        'dataset_sha256':hosted['meta'].get('dataset_sha256')},sort_keys=True)+'\n')
    marker.replace(dist/'version.json')
    if provenance:
        for name,value in (('provenance.json',provenance),('coverage.json',provenance.get('coverage',{}))):
            serialized_report=json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n'
            for folder in (root,dist):
                report=folder/name
                temporary=report.with_suffix('.json.tmp')
                temporary.write_text(serialized_report,encoding='utf-8')
                temporary.replace(report)
    for path,content in ((root/'index.html',html),(dist/'offline.html',html),(dist/'index.html',hosted_html)):
        temporary = path.with_suffix('.html.tmp')
        temporary.write_text(content,encoding='utf-8')
        temporary.replace(path)
    current={path for entries in hosted['meta']['partitions'].values() for path in entries.values()}
    for path in (dist/'records').glob('*.json'):
        if path.relative_to(dist).as_posix() not in current:path.unlink()
    return html


if __name__ == '__main__':
    output = build_site()
    print('Built portable index.html:',round(len(output.encode('utf-8'))/1024),'KiB;',
          'hosted dist/index.html:',round((ROOT/'dist'/'index.html').stat().st_size/1024),'KiB + static result files')
