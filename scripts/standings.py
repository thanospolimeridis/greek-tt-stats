#!/usr/bin/env python3
"""League standings as TTScore publishes them, kept apart from the collector's imports.

imports/standings/ holds standings.csv (one row per team per league group) and its
own provenance.json with requests, coverage and the CSV hash. The numbers are the
source's own table (Wins, Lost, Disq, Pts): nothing is recomputed from fixtures,
because the archive leaves out results it could not validate. The source's "#" is a
draw slot, not a rank, and it publishes no tie-break order, so neither is stored as
a position. The batch collector, its validator and its offline replay never read or
write this folder, and this module is outside batch_import.adapter_hash(). build.py
validates the folder against the canonical catalog and adds it to the published site.
"""
import csv
import hashlib
import html
import json
import re
from pathlib import Path

from import_csv import DataError, integer

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'imports'/'standings'
COLUMNS = ['id', 'event_id', 'group_id', 'category', 'slot', 'club_name', 'team_name', 'club_id',
           'wins', 'losses', 'disqualified', 'points', 'as_of', 'source_id', 'source_url']
HEADERS = ['#', 'Participant', 'Wins', 'Lost', 'Disq', 'Pts']
COUNTS = ('slot', 'wins', 'losses', 'disqualified', 'points')
SOURCE_URL = re.compile(r'https://app\.ttscore\.io/tournament_groups_league\.php\?event=\d+&customer=24')


def digest(body):
    return hashlib.sha256(body).hexdigest()


def clean(text):
    return ' '.join(html.unescape(re.sub(r'<[^>]*>', '', str(text or ''))).split())


def parse_groups(body):
    """Every league group table in one overview response: [(group id, rows, placeholders)].

    A row is {slot, club_name, team_name, wins, losses, disqualified, points}. The
    source labels a team "CLUB - TEAM"; its empty "X - X - BYE" draw slots are counted
    as placeholders and left out. Anything else unexpected raises DataError.
    """
    groups = []
    for block in re.findall(r'<div class="groups"[^>]*\bdata-id="\d+"[^>]*>.*?</table>', body, re.S):
        group = re.search(r'\bdata-id="(\d+)"', block)[1]
        headers = [clean(h) for h in re.findall(r'<th[^>]*>(.*?)</th>', block, re.S)]
        if headers != HEADERS:
            raise DataError(f'Group {group}: standings columns changed: {headers}')
        rows, placeholders = [], 0
        for line in re.findall(r'<tr class="pos-\d+">(.*?)</tr>', block, re.S):
            cells = [clean(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', line, re.S)]
            if len(cells) != len(HEADERS) or not all(re.fullmatch(r'\d+', c) for c in [cells[0], *cells[2:]]):
                raise DataError(f'Group {group}: unreadable standings row {cells}')
            slot, wins, losses, disqualified, points = (int(c) for c in [cells[0], *cells[2:]])
            names = cells[1].split(' - ')
            if names[-1] == 'BYE' and not (wins or losses or disqualified or points):
                placeholders += 1
                continue
            if len(names) != 2 or not all(names):
                raise DataError(f'Group {group}: unexpected team label {cells[1]!r}')
            rows.append({'slot': slot, 'club_name': names[0], 'team_name': names[1], 'wins': wins,
                         'losses': losses, 'disqualified': disqualified, 'points': points})
        if len({r['slot'] for r in rows}) != len(rows):
            raise DataError(f'Group {group}: repeated draw slot')
        groups.append((group, rows, placeholders))
    return groups


def read_rows(path):
    """standings.csv rows as text; the header must be exactly COLUMNS."""
    if not path.exists():
        return []
    with path.open(encoding='utf-8', newline='') as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != COLUMNS:
            raise DataError(f'{path.name}: columns do not match the standings table')
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise DataError(f'{path.name}: inconsistent column count')
    return rows


def load(folder, catalog):
    """Validated standings rows, or None without a manifest."""
    manifest_path = folder/'provenance.json'
    if not manifest_path.exists():
        return None
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    csvs = sorted(folder.glob('*.csv'))
    if manifest.get('csv_sha256') != {p.name: digest(p.read_bytes()) for p in csvs}:
        raise DataError('Standings CSV hash does not match its provenance; re-run import_standings.py')
    requests = manifest.get('requests', {})
    events = {e['id'] for e in catalog.get('events', [])}
    clubs = {c['id'] for c in catalog.get('clubs', [])}
    rows, ids, group_event = [], set(), {}
    for row in read_rows(folder/'standings.csv'):
        label = f"Standing {row['id']}"
        for field in COUNTS:
            row[field] = integer(row[field], f'{label}:{field}')
        if row['id'] != f"ttscore-standing-{row['group_id']}-{row['slot']}" or not row['group_id'].isdigit():
            raise DataError(f'{label}: id does not match its group and slot')
        if row['id'] in ids:
            raise DataError(f'{label}: duplicate row')
        ids.add(row['id'])
        if row['event_id'] not in events:
            raise DataError(f'{label}: unknown event')
        if group_event.setdefault(row['group_id'], row['event_id']) != row['event_id']:
            raise DataError(f'{label}: group belongs to another event')
        if row['club_id'] and row['club_id'] not in clubs:
            raise DataError(f'{label}: unknown club')
        if not row['club_name'] or not row['team_name'] or not row['category']:
            raise DataError(f'{label}: missing team or category label')
        if row['source_id'] not in requests:
            raise DataError(f'{label}: unknown provenance source_id')
        if not SOURCE_URL.fullmatch(row['source_url']):
            raise DataError(f'{label}: unexpected source URL')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['as_of']):
            raise DataError(f'{label}: invalid retrieval date')
        rows.append(row)
    listed = {(g['event'], g['group']): g['rows'] for g in manifest.get('coverage', {}).get('standings', [])}
    found = {}
    for row in rows:
        key = (row['event_id'].removeprefix('ttscore-'), row['group_id'])
        found[key] = found.get(key, 0)+1
    if {k: v for k, v in listed.items() if v} != found:
        raise DataError('Standings rows do not match the coverage listed in their provenance')
    return {'rows': rows, 'manifest': manifest, 'sha256': digest(manifest_bytes),
            'inputs': [{'path': f'imports/standings/{p.name}', 'sha256': digest(p.read_bytes())}
                       for p in [*csvs, manifest_path]]}


def merge(data, table):
    """Add standings to a catalog in place, keeping a deterministic order."""
    if not table:
        return data
    data['standings'] = sorted(table['rows'], key=lambda r: (r['event_id'], int(r['group_id']), r['slot']))
    meta = data.setdefault('meta', {})
    meta['inputs'] = meta.get('inputs', [])+table['inputs']
    meta['league_standings'] = {'sha256': table['sha256'], 'rows': len(table['rows']),
                                'groups': len({r['group_id'] for r in table['rows']}),
                                'events': len({r['event_id'] for r in table['rows']})}
    return data
