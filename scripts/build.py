#!/usr/bin/env python3
"""Build a portable static page without network access or JS dependencies."""
import json
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity_corrections  # noqa: E402
import ranking_history  # noqa: E402
import standings  # noqa: E402

RANKING_FORMAT = 'ranking-snapshots-v1'


def ranking_moves(rows):
    """Give each ranking row the athlete's position in their category's previous list.

    previous_rank is the rank in the category's previous published list, 0 when the
    athlete was not in it, and None for a category's first list. Only lists of the
    same category are compared, at its consecutive published dates.
    """
    from collections import defaultdict
    lists = defaultdict(dict)
    for row in rows:
        lists[(row['category'], row['date'])][row['player_id']] = row
    dates = defaultdict(list)
    for category, date in lists:
        dates[category].append(date)
    for category, published in dates.items():
        published.sort()
        for before, date in zip([None]+published[:-1], published):
            earlier = lists[(category, before)] if before else None
            for player, row in lists[(category, date)].items():
                row['previous_rank'] = None if earlier is None else earlier[player]['rank'] if player in earlier else 0
    return rows


def pack_rankings(rows):
    """Compact ranking rows for the site: per-snapshot fields (date, category, source)
    are stored once and clubs by index. Row ids are omitted; the CSVs keep them. A row
    ends with its previous_rank when it has one (see ranking_moves)."""
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
        row = [by_snapshot[key], r['player_id'], r['rank'], r.get('points'), by_club[club]]
        if r.get('previous_rank') is not None:
            row.append(r['previous_rank'])
        packed.append(row)
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


def club_players(data):
    """Who played team matches for each club: {club id: [[event id, player id, played, won]]}.

    Counts completed singles that belong to a team fixture, with the club taken from
    the match sheet. Club pages need them without loading every player's matches.
    """
    from collections import defaultdict
    counts = defaultdict(lambda: [0, 0])
    for m in data.get('matches', []):
        if m['status'] != 'completed' or not m.get('fixture_id'):
            continue
        for player, club in ((m['player1_id'], m.get('club1_id')), (m['player2_id'], m.get('club2_id'))):
            if club:
                row = counts[club, m['event_id'], player]
                row[0] += 1
                row[1] += m.get('winner_id') == player
    table = defaultdict(list)
    for (club, event, player), (played, won) in sorted(counts.items()):
        table[club].append([event, player, played, won])
    return dict(table)


def partition_results(data, dist, context=None, squads=None):
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
    by_group = defaultdict(list)
    for row in data.get('standings',[]):
        groups['event'][row['event_id']].setdefault('standings',[]).append(row)
        by_group[row['group_id']].append(row)
    # A club's file carries the whole table of every group it played in, so its
    # position can be shown with the same rule as on the league page.
    for rows in by_group.values():
        for club in sorted({r['club_id'] for r in rows if r['club_id']}):
            groups['club'][club].setdefault('standings',[]).extend(rows)
    for club, rows in (squads or {}).items():
        groups['club'][club]['club_players'] = {club: rows}
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


VERSION_FORMAT = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)')


def read_version(root=ROOT):
    """The site's release version, from the committed VERSION file.

    The file is the only source: reading Git or the clock here would make the same
    commit build differently in CI. scripts/release.py is what changes it. A copy
    of the project without the file builds an unversioned site.
    """
    path = root/'VERSION'
    if not path.exists():
        return None
    version = path.read_text(encoding='utf-8').strip()
    if not VERSION_FORMAT.fullmatch(version):
        raise SystemExit(f'VERSION must hold MAJOR.MINOR.PATCH, found {version!r}')
    return version


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


def data_through(data):
    """The dates that tell a visitor how fresh the archive is: the newest result, the day
    the source was last checked for results, and the official ranking in force."""
    results = max((r['date'] for kind in ('matches', 'doubles', 'fixtures') for r in data.get(kind, []) if r.get('date')), default='')
    checked = data.get('meta', {}).get('provenance', {}).get('coverage', {}).get('batch', {}).get('as_of', '')
    rankings = max((r['date'] for r in data.get('rankings', []) if r.get('date')), default='')
    return {key: value for key, value in (('results', results), ('checked', checked), ('rankings', rankings)) if value}


def slim(hosted):
    """Leave out of the hosted page the audit fields it never shows.

    coverage.json, provenance.json and the offline copy keep every one of them. New
    containers are built, so the rows shared with the offline copy stay untouched.
    """
    for kind in ('players', 'events'):
        if kind in hosted:
            hosted[kind] = [{k: v for k, v in row.items() if k not in ('source_id', 'identity_basis')} for row in hosted[kind]]
    provenance = hosted['meta'].get('provenance') or {}
    if isinstance(provenance.get('coverage'), dict):
        coverage = {k: v for k, v in provenance['coverage'].items() if k != 'issues'}
        if isinstance(coverage.get('events'), dict):
            coverage['events'] = {i: {k: v for k, v in e.items() if k != 'adapter_sha256'} for i, e in coverage['events'].items()}
        if isinstance(coverage.get('batch'), dict):
            coverage['batch'] = {k: v for k, v in coverage['batch'].items() if k != 'processed_order'}
        if isinstance(coverage.get('rankings'), list):
            coverage['rankings'] = [{k: v for k, v in r.items() if k != 'source_id'} for r in coverage['rankings']]
        hosted['meta']['provenance'] = {**provenance, 'coverage': coverage}
    return hosted


def build_site(root=ROOT):
    data = json.loads((root/'data'/'catalog.json').read_text(encoding='utf-8'))
    data.setdefault('meta', {})
    # Placeholders keep the key order; the counts are filled in once identities are corrected.
    data['meta']['event_player_counts'] = data['meta']['player_summary'] = None
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
    # Reviewed corrections of source identities, applied last so they reach every table
    # (see identity_corrections.py). Everything below counts corrected identities.
    corrections=identity_corrections.load(root/'data'/'identity-corrections.json',data)
    identity_corrections.apply(data,corrections)
    # Movement since each category's previous list, on the corrected identities.
    ranking_moves(data.get('rankings',[]))
    data['meta']['event_player_counts'], data['meta']['player_summary'] = list_summaries(data)
    through = data_through(data)
    if through:
        data['meta']['data_through'] = through
    css = (root/'src'/'style.css').read_text(encoding='utf-8')
    js = (root/'src'/'app.js').read_text(encoding='utf-8')
    template = (root/'src'/'template.html').read_text(encoding='utf-8')
    import re
    def render(payload):
        # Source text cannot close the JSON element; template markers in data stay literal.
        serialized=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
        replacements={'/*INLINE_CSS*/':css,'/*INLINE_JS*/':js,'/*INLINE_JSON*/':serialized}
        return re.sub(r'/\*INLINE_(?:CSS|JS|JSON)\*/',lambda m:replacements[m[0]],template)
    # Set here and not by the importer, so a release leaves data/catalog.json untouched.
    version=read_version(root)
    if version:data['meta']['version']=version
    context,squads=match_ranks(data),club_players(data)
    html=render({**data,'rankings':pack_rankings(data.get('rankings',[])),
                 **({'match_ranks':pack_match_ranks(context)} if context else {}),
                 **({'club_players':squads} if squads else {})})
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
    slim(hosted)
    hosted['meta']['partitions']=partition_results(data,dist,context,squads)
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
        'dataset_sha256':hosted['meta'].get('dataset_sha256'),
        **({'version':version} if version else {})},sort_keys=True)+'\n')
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
    for name,extra in (('ranking-history-provenance.json',history and history['manifest']),
                       ('standings-provenance.json',table and table['manifest']),
                       ('identity-corrections.json',corrections and corrections['table'])):
        if extra:
            report=dist/name
            temporary=report.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(extra,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
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
