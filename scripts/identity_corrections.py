#!/usr/bin/env python3
"""Reviewed identity corrections, kept apart from the collector's imports.

data/identity-corrections.json lists source identities that a person has reviewed and
found to be the same athlete or the same club, each with the evidence for it: a
registration number that the source mistyped on some match sheets, or one club name
written with different punctuation. The CSVs keep what the source said. build.py
applies the table to the published site, where the corrected profile says which
source identities it includes. The batch collector, its validator and its offline
replay never read the file, and this module is outside batch_import.adapter_hash().

A name alone never justifies an entry: athletes with the same name at the same club
are often different people. The build refuses an entry when the catalog contradicts
it (the two athletes meet or share a doubles match, the merged-away number holds any
official ranking, or the two clubs meet in a fixture) and when a recorded name no
longer matches the catalog.
"""
import hashlib
import json
from pathlib import Path

from import_csv import DataError

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT/'data'/'identity-corrections.json'
VERSION = 1
BASES = {
    'players': ('registration_number_out_of_range', 'registration_number_leading_zero', 'reviewed_same_athlete'),
    'clubs': ('same_name_different_punctuation', 'reviewed_same_club'),
}
FIELDS = ('from', 'to', 'from_name', 'to_name', 'basis', 'evidence')
DOUBLES_MEMBERS = ('player1_id', 'partner1_id', 'player2_id', 'partner2_id')


def digest(body):
    return hashlib.sha256(body).hexdigest()


def mapping(entries, kind, rows):
    """{merged-away id: kept id} for one kind, checked against the catalog rows."""
    names = {r['id']: r.get('name', '') for r in rows}
    result = {}
    for entry in entries:
        if not isinstance(entry, dict) or any(not isinstance(entry.get(k), str) or not entry[k].strip() for k in FIELDS):
            raise DataError(f'Identity corrections: every {kind} entry needs {", ".join(FIELDS)}')
        source, target = entry['from'], entry['to']
        label = f'Identity correction {source} -> {target}'
        if entry['basis'] not in BASES[kind]:
            raise DataError(f'{label}: unknown basis {entry["basis"]!r}')
        if source == target or source in result:
            raise DataError(f'{label}: an identity can be merged once, into another identity')
        for ident, key in ((source, 'from_name'), (target, 'to_name')):
            if ident not in names:
                raise DataError(f'{label}: {ident} is not in the catalog')
            if names[ident] != entry[key]:
                raise DataError(f'{label}: {ident} is now named {names[ident]!r}, not {entry[key]!r}; review the entry again')
        result[source] = target
    chained = sorted(set(result) & set(result.values()))
    if chained:
        raise DataError(f'Identity corrections: {chained[0]} is both merged away and kept')
    return result


def load(path, data):
    """The validated table, or None when the file does not exist."""
    if not path.exists():
        return None
    body = path.read_bytes()
    table = json.loads(body)
    if not isinstance(table, dict) or table.get('version') != VERSION:
        raise DataError(f'Identity corrections: expected an object with version {VERSION}')
    for kind in (*BASES, 'distinct'):
        if not isinstance(table.get(kind, []), list):
            raise DataError(f'Identity corrections: {kind} must be a list')
    players = mapping(table.get('players', []), 'players', data.get('players', []))
    clubs = mapping(table.get('clubs', []), 'clubs', data.get('clubs', []))
    # Same-name athletes reviewed and found to be different people stay apart for good.
    for entry in table.get('distinct', []):
        ids = entry.get('ids') if isinstance(entry, dict) else None
        if not isinstance(ids, list) or len(set(ids)) != 2 or not str(entry.get('evidence', '')).strip():
            raise DataError('Identity corrections: every distinct entry needs two ids and evidence')
        if len({players.get(i, i) for i in ids}) != 2:
            raise DataError(f'Identity corrections: {ids[0]} and {ids[1]} were reviewed as different athletes')
    player, club = (lambda i: players.get(i, i)), (lambda i: clubs.get(i, i))
    for m in data.get('matches', []):
        if player(m['player1_id']) == player(m['player2_id']):
            raise DataError(f"Identity corrections: match {m['id']} is between two identities listed as one athlete")
    for d in data.get('doubles', []):
        members = [player(d[k]) for k in DOUBLES_MEMBERS if d.get(k)]
        if len(set(members)) != len(members):
            raise DataError(f"Identity corrections: doubles {d['id']} holds two identities listed as one athlete")
    for r in data.get('rankings', []):
        if r['player_id'] in players:
            raise DataError(f"Identity corrections: {r['player_id']} holds an official ranking, so it is a real registration")
    for f in data.get('fixtures', []):
        if club(f['home_club_id']) == club(f['away_club_id']):
            raise DataError(f"Identity corrections: fixture {f['id']} is between two identities listed as one club")
    return {'players': players, 'clubs': clubs, 'table': table, 'sha256': digest(body),
            'inputs': [{'path': 'data/'+path.name, 'sha256': digest(body)}]}


def merged_names(kept, removed):
    """Alias text for a kept row: every other spelling the source used, without the display name."""
    names = set(filter(None, kept.get('aliases', '').split('|')))
    for row in removed:
        names |= {row['name'], *filter(None, row.get('aliases', '').split('|'))}
    return '|'.join(sorted(names-{kept['name']}))


def apply(data, corrections):
    """Rewrite merged identities across a catalog in place, keeping a deterministic order."""
    if not corrections:
        return data
    for kind in ('players', 'clubs'):
        table = corrections[kind]
        by_id = {r['id']: r for r in data.get(kind, [])}
        for target in sorted(set(table.values())):
            removed = [by_id[source] for source in sorted(table) if table[source] == target]
            by_id[target]['aliases'] = merged_names(by_id[target], removed)
        if kind in data:
            data[kind] = [r for r in data[kind] if r['id'] not in table]
    player, club = (lambda i: corrections['players'].get(i, i)), (lambda i: corrections['clubs'].get(i, i))
    rewrites = {'players': {'club_id': club},
                'matches': {'player1_id': player, 'player2_id': player, 'winner_id': player, 'club1_id': club, 'club2_id': club},
                'doubles': {key: player for key in DOUBLES_MEMBERS},
                'fixtures': {'home_club_id': club, 'away_club_id': club},
                'rankings': {'player_id': player, 'club_id': club},
                'standings': {'club_id': club}}
    for kind, fields in rewrites.items():
        for row in data.get(kind, []):
            for field, canonical in fields.items():
                if row.get(field):
                    row[field] = canonical(row[field])
    meta = data.setdefault('meta', {})
    meta['inputs'] = meta.get('inputs', [])+corrections['inputs']
    # The site reads the two maps to keep old links working and to name merged identities.
    meta['identity_corrections'] = {'sha256': corrections['sha256'],
                                    'players': dict(sorted(corrections['players'].items())),
                                    'clubs': dict(sorted(corrections['clubs'].items()))}
    return data
