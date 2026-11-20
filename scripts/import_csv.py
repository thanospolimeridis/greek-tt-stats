#!/usr/bin/env python3
"""Build a reproducible, source-labelled site dataset from CSV files.

No external dependencies. Do not infer outcomes or rankings from event listings.
CSV filenames: events.csv, players.csv, clubs.csv, matches.csv, rankings.csv,
fixtures.csv. Missing files imply no records of that type.
"""
import argparse
import csv
import datetime as dt
import json
import hashlib
import math
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TYPES = ('events', 'players', 'clubs', 'matches', 'rankings', 'fixtures', 'doubles')
REQUIRED = {
    'doubles': ('id','event_id','date','side1_name','side2_name','winner_side','status','score1','score2','games','source_url'),
    'events': ('id', 'name', 'season', 'source_url'),
    'players': ('id', 'name'),
    'clubs': ('id', 'name'),
    'matches': ('id', 'event_id', 'date', 'player1_id', 'player2_id', 'status'),
    'rankings': ('id', 'player_id', 'category', 'date', 'rank', 'source_url'),
    'fixtures': ('id', 'event_id', 'home_club_id', 'away_club_id', 'status'),
}

class DataError(ValueError):
    pass


def source_url(value):
    if not value:
        return ''
    parsed = urlparse(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or re.search(r'[\s<>"\\]', value):
        raise DataError(f'Invalid public source URL: {value}')
    return value


def date(value, context):
    if value:
        try:
            return dt.date.fromisoformat(value).isoformat()
        except ValueError:
            raise DataError(f'{context}: invalid ISO date: {value}') from None
    return ''


def unique(items, context):
    seen = set()
    for row in items:
        ident = row['id']
        if not ident or ident in seen:
            raise DataError(f'{context}: empty/duplicate ID {ident!r}')
        seen.add(ident)


def read_csv(path, kind):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
            raise DataError(f'{path.name}: duplicate columns')
        missing = set(REQUIRED[kind]) - set(reader.fieldnames or ())
        if missing:
            raise DataError(f'{path.name}: missing columns {sorted(missing)}')
        rows = []
        for i, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise DataError(f'{path.name}:{i}: inconsistent column count')
            result = {str(k).strip(): (v or '').strip() for k, v in row.items() if k}
            for key in REQUIRED[kind]:
                if not result.get(key):
                    raise DataError(f'{path.name}:{i}: required field {key} is empty')
            for k in ('source_url',):
                if k in result:
                    result[k] = source_url(result[k])
            for k in ('date', 'start_date', 'end_date'):
                if k in result:
                    result[k] = date(result[k], f'{path.name}:{i}')
            rows.append(result)
    unique(rows, path.name)
    return rows


def integer(s, context, allow_blank=False):
    if not s and allow_blank:
        return None
    try:
        n = int(s)
        if n < 0:
            raise ValueError
        return n
    except ValueError:
        raise DataError(f'{context}: expected non-negative integer, got {s!r}') from None


def parse_games(value, label, completed=True):
    if not value:
        return []
    out = []
    for game in value.split('|'):
        match = re.fullmatch(r'\s*(\d+)\s*[:\-]\s*(\d+)\s*', game)
        if not match:
            raise DataError(f'{label}: invalid game score {game!r}; use 11:8|9:11|...')
        a, b = map(int, match.groups())
        if completed and not (max(a,b) == 11 and min(a,b) <= 9 or max(a,b) > 11 and abs(a-b) == 2):
            raise DataError(f'{label}: invalid completed game score {game!r}')
        out.append([a, b])
    return out


def build(input_dir, seed_file):
    data = {kind: read_csv(input_dir / f'{kind}.csv', kind) for kind in TYPES}
    seeds = json.loads(seed_file.read_text(encoding='utf-8'))
    unique(seeds, 'seed events')
    for row in seeds:
        if any(not row.get(k) for k in REQUIRED['events']):
            raise DataError('Seed event: missing required field')
        source_url(row['source_url'])
        for key in ('start_date', 'end_date'):
            date(row.get(key, ''), 'Seed event')
    # A CSV event row takes precedence only when its source is explicit.
    merged = {row['id']: row for row in seeds}
    for row in data['events']:
        merged[row['id']] = {**merged.get(row['id'], {}), **row}
    imported_ids = {row['id'] for row in data['events']}
    legacy_ids = sorted(set(merged) - imported_ids) if imported_ids else []
    for ident in legacy_ids:
        merged[ident]['source_status'] = 'legacy_not_in_current_catalog'
    data['events'] = sorted(merged.values(), key=lambda r: (r.get('start_date', ''), r['id']), reverse=True)
    for kind in TYPES:
        unique(data[kind], kind)
        data[kind].sort(key=lambda r: r['id'])
    data['events'].sort(key=lambda r: (r.get('start_date',''),r['id']), reverse=True)
    for row in data['events']:
        if row.get('start_date') and row.get('end_date') and row['start_date'] > row['end_date']:
            raise DataError(f"Event {row['id']}: end date precedes start date")
    by_id = {kind: {r['id']: r for r in data[kind]} for kind in TYPES}
    for row in data['players']:
        if row.get('club_id') and row['club_id'] not in by_id['clubs']:
            raise DataError(f"Player {row['id']}: missing club {row['club_id']}")
    for row in data['matches']:
        ident = row['id']
        if row['event_id'] not in by_id['events']:
            raise DataError(f'{ident}: missing event')
        p1, p2 = row['player1_id'], row['player2_id']
        if p1 not in by_id['players'] or p2 not in by_id['players'] or p1 == p2:
            raise DataError(f'{ident}: invalid player IDs')
        status = row['status'].lower()
        if status not in ('completed','walkover','retired','cancelled','scheduled'):
            raise DataError(f'{ident}: unsupported status {status}')
        row['status'] = status
        row['games'] = parse_games(row.get('games', ''), ident, status == 'completed')
        best_of = integer(row.get('best_of') or '5', f'{ident}:best_of')
        if best_of not in (1,3,5,7,9):
            raise DataError(f'{ident}: best_of must be an odd number from 1 to 9')
        row['best_of'] = best_of
        if status in ('completed','retired','walkover'):
            if row.get('winner_id') not in (p1,p2):
                raise DataError(f'{ident}: winner must be one of the players')
        elif row.get('winner_id'):
            raise DataError(f'{ident}: unplayed match cannot have winner')
        if status == 'completed':
            if not row['games'] and (not row.get('score1') or not row.get('score2')):
                raise DataError(f'{ident}: completed match needs set score or game scores')
            won1 = sum(a > b for a,b in row['games'])
            won2 = sum(b > a for a,b in row['games'])
            s1 = integer(row.get('score1',''), f'{ident}:score1', allow_blank=True)
            s2 = integer(row.get('score2',''), f'{ident}:score2', allow_blank=True)
            if row['games'] and ((s1 is not None and won1 != s1) or (s2 is not None and won2 != s2)):
                raise DataError(f'{ident}: set score and individual games do not agree')
            if s1 is None and row['games']: s1 = won1
            if s2 is None and row['games']: s2 = won2
            if s1 is not None and s2 is not None:
                if s1 == s2 or (row['winner_id']==p1) != (s1>s2):
                    raise DataError(f'{ident}: winner and set score disagree')
            row['score1'], row['score2'] = s1, s2
            target = best_of // 2 + 1
            if max(s1,s2) != target or min(s1,s2) >= target:
                raise DataError(f'{ident}: invalid final score for best_of={best_of}')
            a = b = 0
            for ga, gb in row['games']:
                if max(a,b) == target:
                    raise DataError(f'{ident}: games after match was decided')
                a += ga > gb
                b += gb > ga
        else:
            row['score1'] = integer(row.get('score1',''),f'{ident}:score1',allow_blank=True)
            row['score2'] = integer(row.get('score2',''),f'{ident}:score2',allow_blank=True)
        for key in ('club1_id','club2_id'):
            if row.get(key) and row[key] not in by_id['clubs']:
                raise DataError(f'{ident}: unknown club {row[key]}')
        if not row.get('source_url'):
            raise DataError(f'{ident}: match needs source_url for verification')
        if row.get('fixture_id'):
            fixture = by_id['fixtures'].get(row['fixture_id'])
            if not fixture or fixture['event_id'] != row['event_id']:
                raise DataError(f'{ident}: invalid fixture reference')
            if row.get('club1_id') != fixture['home_club_id'] or row.get('club2_id') != fixture['away_club_id']:
                raise DataError(f'{ident}: fixture clubs disagree')
    for row in data['doubles']:
        ident = row['id']
        if row['event_id'] not in by_id['events']:
            raise DataError(f'{ident}: missing doubles event')
        if row['status'] != 'completed' or row['winner_side'] not in ('1','2'):
            raise DataError(f'{ident}: unsupported doubles outcome')
        row['games'] = parse_games(row['games'], ident)
        a,b = integer(row['score1'], ident), integer(row['score2'], ident)
        best_of = integer(row.get('best_of') or '5', ident)
        if best_of not in (1,3,5,7,9):raise DataError(f'{ident}: invalid doubles best_of')
        target = best_of//2+1
        if max(a,b) != target or min(a,b) >= target or (a>b) != (row['winner_side']=='1'):
            raise DataError(f'{ident}: doubles score/winner disagreement')
        counts=[0,0]
        for ga,gb in row['games']:
            if max(counts)==target: raise DataError(f'{ident}: games after doubles decided')
            counts[0 if ga>gb else 1]+=1
        if counts != [a,b]: raise DataError(f'{ident}: doubles game totals disagree')
        row['score1'],row['score2']=a,b
        members=[row.get(k,'') for k in ('player1_id','partner1_id','player2_id','partner2_id')]
        if any(members) and (len(set(members))!=4 or any(p not in by_id['players'] for p in members)):
            raise DataError(f'{ident}: invalid doubles members')
        identity = 'resolved_members' if all(members) else 'source_pair_labels_only'
        if row.get('identity_status',identity) != identity:
            raise DataError(f'{ident}: doubles identity status disagrees with members')
        row['identity_status'] = identity
        row['best_of'] = best_of
        if row.get('fixture_id') and (row['fixture_id'] not in by_id['fixtures'] or by_id['fixtures'][row['fixture_id']]['event_id']!=row['event_id']):
            raise DataError(f'{ident}: invalid doubles fixture')
        if not row['source_url']: raise DataError(f'{ident}: doubles source required')
    ranking_keys = set()
    for row in data['rankings']:
        key = (row['player_id'],row['category'],row['date'])
        if key in ranking_keys:
            raise DataError('Duplicate player/category/date ranking')
        ranking_keys.add(key)
        if row['player_id'] not in by_id['players']:
            raise DataError(f"Ranking {row['id']}: unknown player")
        row['rank'] = integer(row['rank'], f"Ranking {row['id']}:rank")
        if row['rank'] < 1:
            raise DataError(f"Ranking {row['id']}: rank must be >=1")
        try:
            row['points'] = float(row['points']) if row.get('points') else None
        except ValueError:
            raise DataError(f"Ranking {row['id']}: invalid points") from None
        if row['points'] is not None and (not math.isfinite(row['points']) or row['points'] < 0):
            raise DataError(f"Ranking {row['id']}: points must be finite and non-negative")
    for row in data['fixtures']:
        if row['event_id'] not in by_id['events']:
            raise DataError(f"Fixture {row['id']}: unknown event")
        for field in ('home_club_id','away_club_id'):
            if row[field] not in by_id['clubs']:
                raise DataError(f"Fixture {row['id']}: unknown club {row[field]}")
        if row['home_club_id'] == row['away_club_id']:
            raise DataError(f"Fixture {row['id']}: identical clubs")
        row['status']=row['status'].lower()
        if row['status'] not in ('completed','scheduled','cancelled'):
            raise DataError(f"Fixture {row['id']}: unknown status")
        for field in ('home_score','away_score'):
            row[field] = integer(row.get(field,''),f"Fixture {row['id']}:{field}",allow_blank=True)
        if row['status']=='completed' and (row['home_score'] is None or row['away_score'] is None):
            raise DataError(f"Fixture {row['id']}: missing score")
        if not row.get('source_url'):
            raise DataError(f"Fixture {row['id']}: needs source_url")
    inputs = [{'path': 'seed/'+seed_file.name, 'sha256':hashlib.sha256(seed_file.read_bytes()).hexdigest()}]
    inputs += [{'path': 'imports/'+p.name, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(input_dir.glob('*.csv'))]
    manifest_path = input_dir/'provenance.json'
    provenance = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if provenance:
        expected = provenance.get('csv_sha256', {})
        actual = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(input_dir.glob('*.csv'))}
        if expected != actual:
            raise DataError('Provenance CSV hashes do not match; re-run source import')
        requests = provenance.get('requests', {})
        for kind in TYPES:
            for row in data[kind]:
                if row.get('source_id') and row['source_id'] not in requests:
                    raise DataError(f"{kind} {row['id']}: unknown provenance source_id")
    season_coverage = {}
    for season in sorted({e['season'] for e in data['events']}):
        ids = {e['id'] for e in data['events'] if e['season']==season}
        singles = [m for m in data['matches'] if m['event_id'] in ids and m['status']=='completed']
        doubles = [m for m in data['doubles'] if m['event_id'] in ids]
        season_coverage[season] = {'catalog_events':len(ids),'events_with_results':len({m['event_id'] for m in singles+doubles}),'singles':len(singles),'doubles':len(doubles)}
    data['meta'] = {
        'season_coverage':season_coverage,
        'schema_version': 3,
        'product': 'Greek Table Tennis Statistics',
        'dataset_sha256': hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
        'inputs': inputs,
        'provenance': provenance,
        'historical_coverage': 'partial',
        'legacy_events_not_in_current_catalog': legacy_ids,
        'source': 'TTScore public event pages + explicitly imported records',
        'data_coverage': ('event_catalog_only' if not data['matches'] and not data['doubles'] else 'imported_match_records'),
        'verified_results': sum(m['status']=='completed' for m in data['matches']),
        'events_with_results': len({m['event_id'] for m in data['matches']+data['doubles'] if m['status']=='completed'}),
        'disclaimer': 'Event listings do not imply match-result coverage. Rankings must come from official published snapshots.'
    }
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=ROOT/'imports')
    p.add_argument('--seed',type=Path,default=ROOT/'data'/'verified_events.json')
    p.add_argument('--output',type=Path,default=ROOT/'data'/'catalog.json')
    args=p.parse_args()
    try:
        data=build(args.input,args.seed)
    except (DataError, ValueError, OSError) as exc:
        print('IMPORT FAILED:',exc,file=sys.stderr)
        sys.exit(1)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix+'.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(args.output)
    print('Built',args.output, {k:len(data[k]) for k in TYPES})

if __name__=='__main__':
    main()
