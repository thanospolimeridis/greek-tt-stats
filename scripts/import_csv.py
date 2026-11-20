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
import math
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TYPES = ('events', 'players', 'clubs', 'matches', 'rankings', 'fixtures')
REQUIRED = {
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
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
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
        missing = set(REQUIRED[kind]) - set(reader.fieldnames or ())
        if missing:
            raise DataError(f'{path.name}: missing columns {sorted(missing)}')
        rows = []
        for i, row in enumerate(reader, 2):
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


def parse_games(value, label):
    if not value:
        return []
    out = []
    for game in value.split('|'):
        match = re.fullmatch(r'\s*(\d+)\s*[:\-]\s*(\d+)\s*', game)
        if not match:
            raise DataError(f'{label}: invalid game score {game!r}; use 11:8|9:11|...')
        a, b = map(int, match.groups())
        if a == b:
            raise DataError(f'{label}: tied game score {game!r}')
        out.append([a, b])
    return out


def build(input_dir, seed_file):
    data = {kind: read_csv(input_dir / f'{kind}.csv', kind) for kind in TYPES}
    seeds = json.loads(seed_file.read_text(encoding='utf-8'))
    # A CSV event row takes precedence only when its source is explicit.
    merged = {row['id']: row for row in seeds}
    merged.update({row['id']: row for row in data['events']})
    data['events'] = sorted(merged.values(), key=lambda r: (r.get('start_date', ''), r['id']), reverse=True)
    for kind in TYPES:
        unique(data[kind], kind)
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
        row['games'] = parse_games(row.get('games', ''), ident)
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
            if row['games'] and s1 is not None and s2 is not None and (won1,won2)!=(s1,s2):
                raise DataError(f'{ident}: set score and individual games do not agree')
            if s1 is None and row['games']: s1 = won1
            if s2 is None and row['games']: s2 = won2
            if s1 is not None and s2 is not None:
                if s1 == s2 or (row['winner_id']==p1) != (s1>s2):
                    raise DataError(f'{ident}: winner and set score disagree')
            row['score1'], row['score2'] = s1, s2
        else:
            row['score1'] = integer(row.get('score1',''),f'{ident}:score1',allow_blank=True)
            row['score2'] = integer(row.get('score2',''),f'{ident}:score2',allow_blank=True)
        for key in ('club1_id','club2_id'):
            if row.get(key) and row[key] not in by_id['clubs']:
                raise DataError(f'{ident}: unknown club {row[key]}')
        if not row.get('source_url'):
            raise DataError(f'{ident}: match needs source_url for verification')
    for row in data['rankings']:
        if row['player_id'] not in by_id['players']:
            raise DataError(f"Ranking {row['id']}: unknown player")
        row['rank'] = integer(row['rank'], f"Ranking {row['id']}:rank")
        if row['rank'] < 1:
            raise DataError(f"Ranking {row['id']}: rank must be >=1")
        row['points'] = float(row['points']) if row.get('points') else None
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
    data['meta'] = {
        'product': 'Greek Table Tennis Statistics',
        'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'source': 'TTScore public event pages + explicitly imported records',
        'data_coverage': ('event_catalog_only' if not data['matches'] else 'imported_match_records'),
        'verified_results': sum(m['status']=='completed' for m in data['matches']),
        'events_with_results': len({m['event_id'] for m in data['matches'] if m['status']=='completed'}),
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
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Built',args.output, {k:len(data[k]) for k in TYPES})

if __name__=='__main__':
    main()
