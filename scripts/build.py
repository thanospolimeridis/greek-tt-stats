#!/usr/bin/env python3
"""Build a portable static page without network access or JS dependencies."""
import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ranking_history  # noqa: E402

RANKING_FORMAT = 'ranking-snapshots-v1'


def pack_rankings(rows):
    """Compact ranking rows for the site: per-snapshot fields (date, category, source)
    are stored once and clubs by index. Row ids are omitted; the CSVs keep them."""
    snapshots, clubs, by_snapshot, by_club, packed = [], [], {}, {}, []
    for r in rows:
        key = (r['date'], r['category'], r.get('source_id', ''), r.get('source_url', ''))
        if key not in by_snapshot:
            by_snapshot[key] = len(snapshots)
            snapshots.append(list(key))
        club = r.get('club_id', '') or ''
        if club not in by_club:
            by_club[club] = len(clubs)
            clubs.append(club)
        packed.append([by_snapshot[key], r['player_id'], r['rank'], r.get('points'), by_club[club]])
    return {'format': RANKING_FORMAT, 'snapshots': snapshots, 'clubs': clubs, 'rows': packed}


def partition_results(data, dist):
    """Build static route files; shared rows are copied, never inferred or aggregated."""
    from collections import defaultdict
    groups = {kind:defaultdict(lambda: {'matches':[], 'doubles':[], 'fixtures':[]})
              for kind in ('event','club')}
    # Ranking history is too large for the main page: each player's file carries
    # their snapshots, and each past snapshot date gets its own file.
    for kind in ('player','ranking'):
        groups[kind] = defaultdict(lambda: {'matches':[], 'doubles':[], 'fixtures':[], 'rankings':[]})
    for row in data.get('rankings',[]):
        groups['player'][row['player_id']]['rankings'].append(row)
        groups['ranking'][row['date']]['rankings'].append(row)
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
            if 'rankings' in records:records={**records,'rankings':pack_rankings(records['rankings'])}
            body=json.dumps(records,ensure_ascii=False,separators=(',',':'))+'\n'
            name=kind+'-'+hashlib.sha256(body.encode()).hexdigest()[:24]+'.json'
            (folder/name).write_text(body,encoding='utf-8')
            paths[kind][ident]='records/'+name
    return paths


def list_summaries(data):
    """Counts for list pages, which load no result files. Completed singles only."""
    from collections import Counter, defaultdict
    entrants, played, won = defaultdict(set), Counter(), Counter()
    for m in data.get('matches', []):
        if m['status'] != 'completed':
            continue
        for ident in (m['player1_id'], m['player2_id']):
            entrants[m['event_id']].add(ident)
            played[ident] += 1
        if m.get('winner_id'):
            won[m['winner_id']] += 1
    return ({ident: len(players) for ident, players in sorted(entrants.items())},
            {ident: [played[ident], won[ident]] for ident in sorted(played)})


def build_site(root=ROOT):
    data = json.loads((root/'data'/'catalog.json').read_text(encoding='utf-8'))
    data.setdefault('meta', {})
    data['meta']['event_player_counts'], data['meta']['player_summary'] = list_summaries(data)
    provenance=data.get('meta',{}).get('provenance',{})
    # Keep the detailed audit downloadable without parsing every request in the UI.
    if provenance:
        data['meta']['provenance']={k:v for k,v in provenance.items() if k!='requests'}
    # Official ranking history lives outside the collector's imports (see ranking_history.py).
    history=ranking_history.load(root/'imports'/'ranking-history',data)
    ranking_history.merge(data,history)
    css = (root/'src'/'style.css').read_text(encoding='utf-8')
    js = (root/'src'/'app.js').read_text(encoding='utf-8')
    template = (root/'src'/'template.html').read_text(encoding='utf-8')
    import re
    def render(payload):
        # Source text cannot close the JSON element; template markers in data stay literal.
        serialized=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
        replacements={'/*INLINE_CSS*/':css,'/*INLINE_JS*/':js,'/*INLINE_JSON*/':serialized}
        return re.sub(r'/\*INLINE_(?:CSS|JS|JSON)\*/',lambda m:replacements[m[0]],template)
    html=render({**data,'rankings':pack_rankings(data.get('rankings',[]))})
    dist = root/'dist'
    dist.mkdir(exist_ok=True)
    latest={}
    for row in data.get('rankings',[]):
        latest[row['category']]=max(latest.get(row['category'],''),row['date'])
    hosted={**data,'matches':[],'doubles':[],'fixtures':[],'meta':dict(data.get('meta',{})),
            # Inline copy of the latest snapshot only; each player's file and each
            # snapshot date file carry the rest.
            'rankings':pack_rankings([r for r in data.get('rankings',[]) if r['date']==latest[r['category']]])}
    hosted['meta']['partitions']=partition_results(data,dist)
    dates_by_category={}
    for row in data.get('rankings',[]):
        dates_by_category.setdefault(row['category'],set()).add(row['date'])
    hosted['meta']['ranking_dates']={c:sorted(d,reverse=True) for c,d in sorted(dates_by_category.items())}
    hosted['meta']['table_counts']={kind:len(data.get(kind,[])) for kind in ('matches','doubles','fixtures','rankings')}
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
    if history:
        # Published in dist/ only: an untracked file in the checkout would stop the collector.
        report=dist/'ranking-history-provenance.json'
        temporary=report.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(history['manifest'],ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
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
