#!/usr/bin/env python3
"""Official ranking history, kept apart from the collector's imports.

imports/ranking-history/ holds rankings-YYYY.csv shards (the rankings.csv columns),
players.csv for athletes who appear only in rankings, and its own provenance.json
with requests, coverage and CSV hashes. The batch collector, its validator and its
offline replay never read or write this folder, and this module is outside
batch_import.adapter_hash(). build.py validates the folder against the canonical
catalog and merges it into the published site; existing catalog rows always win.
"""
import hashlib
import json
import math
from pathlib import Path

from import_csv import DataError, integer, read_csv

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'imports'/'ranking-history'
COLUMNS = ['id', 'player_id', 'category', 'date', 'rank', 'source_url', 'club_id', 'points', 'source_id']
PLAYER_COLUMNS = ['id', 'name', 'aliases', 'club_as_of', 'club_id', 'identity_basis', 'source_id']
MAX_SHARD_BYTES = 25_000_000


def digest(body):
    return hashlib.sha256(body).hexdigest()


def shard_name(date):
    return f'rankings-{date[:4]}.csv'


def load(folder, catalog):
    """Validated history rows and ranking-only players, or None without a manifest."""
    manifest_path = folder/'provenance.json'
    if not manifest_path.exists():
        return None
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    csvs = sorted(folder.glob('*.csv'))
    if manifest.get('csv_sha256') != {p.name: digest(p.read_bytes()) for p in csvs}:
        raise DataError('Ranking history CSV hashes do not match its provenance; re-run import_rankings.py')
    requests = manifest.get('requests', {})
    base_players = {p['id'] for p in catalog['players']}
    clubs = {c['id'] for c in catalog['clubs']}
    players = []
    for row in read_csv(folder/'players.csv', 'players'):
        if row.get('source_id') not in requests:
            raise DataError(f"History player {row['id']}: unknown provenance source_id")
        if row.get('club_id') and row['club_id'] not in clubs:
            raise DataError(f"History player {row['id']}: unknown club")
        if row['id'] not in base_players:  # the catalog's own identity always wins
            players.append(row)
    if len({p['id'] for p in players}) != len(players):
        raise DataError('Ranking history: duplicate player rows')
    known = base_players | {p['id'] for p in players}
    seen = {(r['player_id'], r['category'], r['date']) for r in catalog['rankings']}
    ids = {r['id'] for r in catalog['rankings']}
    rows = []
    for path in csvs:
        if path.name == 'players.csv':
            continue
        if path.stat().st_size > MAX_SHARD_BYTES:
            raise DataError(f'{path.name}: shard exceeds {MAX_SHARD_BYTES} bytes; split it further')
        for row in read_csv(path, 'rankings'):
            label = f"History ranking {row['id']}"
            if shard_name(row['date']) != path.name:
                raise DataError(f'{label}: belongs in {shard_name(row["date"])}')
            if row.get('source_id') not in requests:
                raise DataError(f'{label}: unknown provenance source_id')
            if row['player_id'] not in known:
                raise DataError(f'{label}: unknown player')
            if row.get('club_id') and row['club_id'] not in clubs:
                raise DataError(f'{label}: unknown club')
            key = (row['player_id'], row['category'], row['date'])
            if key in seen or row['id'] in ids:
                raise DataError(f'{label}: duplicate player/category/date ranking')
            seen.add(key)
            ids.add(row['id'])
            row['rank'] = integer(row['rank'], f'{label}:rank')
            if row['rank'] < 1:
                raise DataError(f'{label}: rank must be >=1')
            try:
                row['points'] = float(row['points']) if row.get('points') else None
            except ValueError:
                raise DataError(f'{label}: invalid points') from None
            if row['points'] is not None and (not math.isfinite(row['points']) or row['points'] < 0):
                raise DataError(f'{label}: points must be finite and non-negative')
            rows.append(row)
    public = {k: v for k, v in manifest.items() if k != 'requests'}
    return {'players': players, 'rankings': rows, 'manifest': manifest, 'public': public,
            'sha256': digest(manifest_bytes),
            'inputs': [{'path': f'imports/ranking-history/{p.name}', 'sha256': digest(p.read_bytes())}
                       for p in [*csvs, manifest_path]]}


def merge(data, history):
    """Add history to a catalog in place, keeping a deterministic order."""
    if not history:
        return data
    data['players'] = sorted(data['players']+history['players'], key=lambda r: r['id'])
    data['rankings'] = sorted(data['rankings']+history['rankings'], key=lambda r: r['id'])
    meta = data.setdefault('meta', {})
    # Copies: the collector's own provenance download must not list history snapshots
    # whose requests live in the history manifest.
    provenance = dict(meta.get('provenance', {}))
    coverage = dict(provenance.get('coverage', {}))
    coverage['rankings'] = sorted(coverage.get('rankings', [])+history['manifest']['coverage']['rankings'],
                                  key=lambda r: (r['date'], r['category']))
    provenance['coverage'] = coverage
    meta['provenance'] = provenance
    meta['inputs'] = meta.get('inputs', [])+history['inputs']
    meta['ranking_history'] = {'sha256': history['sha256'], 'rows': len(history['rankings']),
                               'snapshots': len(history['manifest']['coverage']['rankings']),
                               'players_added': len(history['players'])}
    return data
