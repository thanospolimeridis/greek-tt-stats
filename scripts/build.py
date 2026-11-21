#!/usr/bin/env python3
"""Build a portable static page without network access or JS dependencies."""
import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ranking_history  # noqa: E402
import standings  # noqa: E402

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


MATCH_RANK_FORMAT = 'match-ranks-v1'


def match_ranks(data):
    """Both players' official positions on the day of each completed singles match.

    The ranking in force is the latest snapshot published on or before the match
    date. Positions are read from the widest list of that snapshot that holds both
    players (the senior list of their gender, which includes its juniors), or the
    one player's widest list when only one is ranked. Matches before the first
    snapshot, between two unranked players, or between players with no list in
    common get no entry. This joins two source tables; nothing is estimated.
    Returns {match id: (snapshot date, category, position 1, position 2)}.
    """
    from bisect import bisect_right
    from collections import Counter, defaultdict
    positions, sizes = defaultdict(lambda: defaultdict(dict)), Counter()
    for row in data.get('rankings', []):
        positions[row['date']][row['player_id']][row['category']] = row['rank']
        sizes[row['date'], row['category']] += 1
    dates, context = sorted(positions), {}
    for m in data.get('matches', []):
        index = bisect_right(dates, m.get('date') or '')-1
        if m['status'] != 'completed' or index < 0:
            continue
        date = dates[index]
        first, second = positions[date].get(m['player1_id'], {}), positions[date].get(m['player2_id'], {})
        lists = [c for c in first if c in second] if first and second else list(first or second)
        if lists:
            category = max(lists, key=lambda c: (sizes[date, c], c))
            context[m['id']] = (date, category, first.get(category), second.get(category))
    return context


def pack_match_ranks(context, ids=None):
    """Compact form for the site: snapshot dates and categories are stored once."""
    dates, categories, rows = {}, {}, {}
    for ident in sorted(context if ids is None else ids):
        if ident in context:
            date, category, first, second = context[ident]
            rows[ident] = [dates.setdefault(date, len(dates)), categories.setdefault(category, len(categories)), first, second]
    return {'format': MATCH_RANK_FORMAT, 'dates': list(dates), 'categories': list(categories), 'rows': rows}


def partition_results(data, dist, context=None):
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
    # A player's file also carries the ranking positions for their own matches.
    for ident, records in groups['player'].items():
        packed = pack_match_ranks(context or {}, [m['id'] for m in records['matches']])
        if packed['rows']:records['match_ranks'] = packed
    # Only league files gain the key, so every other event file keeps its bytes.
    for row in data.get('standings',[]):
        groups['event'][row['event_id']].setdefault('standings',[]).append(row)
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
    # League standings as the source publishes them, also outside the collector (see standings.py).
    table=standings.load(root/'imports'/'standings',data)
    standings.merge(data,table)
    css = (root/'src'/'style.css').read_text(encoding='utf-8')
    js = (root/'src'/'app.js').read_text(encoding='utf-8')
    template = (root/'src'/'template.html').read_text(encoding='utf-8')
    import re
    def render(payload):
        # Source text cannot close the JSON element; template markers in data stay literal.
        serialized=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
        replacements={'/*INLINE_CSS*/':css,'/*INLINE_JS*/':js,'/*INLINE_JSON*/':serialized}
        return re.sub(r'/\*INLINE_(?:CSS|JS|JSON)\*/',lambda m:replacements[m[0]],template)
    context=match_ranks(data)
    html=render({**data,'rankings':pack_rankings(data.get('rankings',[])),
                 **({'match_ranks':pack_match_ranks(context)} if context else {})})
    dist = root/'dist'
    dist.mkdir(exist_ok=True)
    latest={}
    for row in data.get('rankings',[]):
        latest[row['category']]=max(latest.get(row['category'],''),row['date'])
    hosted={**data,'matches':[],'doubles':[],'fixtures':[],'meta':dict(data.get('meta',{})),
            # Inline copy of the latest snapshot only; each player's file and each
            # snapshot date file carry the rest.
            'rankings':pack_rankings([r for r in data.get('rankings',[]) if r['date']==latest[r['category']]])}
    if table:hosted['standings']=[]  # each league's file carries its own rows
    hosted['meta']['partitions']=partition_results(data,dist,context)
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
    # Published in dist/ only: an untracked file in the checkout would stop the collector.
    for name,extra in (('ranking-history-provenance.json',history),('standings-provenance.json',table)):
        if extra:
            report=dist/name
            temporary=report.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(extra['manifest'],ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
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
