#!/usr/bin/env python3
"""Add official TTScore ranking snapshots to imports/ranking-history/.

Each snapshot is one public read-only request (category x date) fetched with the
same client, cache format and parser as ttscore.py. Rows go into yearly shards
(rankings-YYYY.csv, the rankings.csv columns); athletes not yet known anywhere go
into players.csv; the folder's own provenance.json gains the request records, one
coverage entry per snapshot and refreshed CSV hashes. The collector's imports are
only read, never written. A snapshot that fails validation is rejected whole and
listed in coverage. Any HTTP or network failure stops the run before anything is
written. The finished folder is validated with ranking_history.load().

    python3 scripts/import_rankings.py --cache capture/ttscore-rankings --category 15 --category 10
    python3 scripts/import_rankings.py ... --offline   # rebuild from the cache only
"""
import argparse
import csv
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ttscore import ROOT, Client, DataError, Importer, digest, options  # noqa: E402
from import_csv import build  # noqa: E402
import ranking_history  # noqa: E402

ADAPTER = 'ttscore-ranking-history-v1'


def read_rows(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8', newline='') as source:
        return list(csv.DictReader(source))


def write_rows(path, columns, rows):
    with path.open('w', encoding='utf-8', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=columns, extrasaction='raise')
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: r['id']))


def merge_player(old, new):
    """Same identity seen in several snapshots: keep the newest club, collect names."""
    base, other = (new, old) if new.get('club_as_of', '') >= old.get('club_as_of', '') else (old, new)
    names = set(filter(None, base.get('aliases', '').split('|') + other.get('aliases', '').split('|') + [other['name']]))
    return {**base, 'aliases': '|'.join(sorted(names - {base['name']}))}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--imports', type=Path, default=ROOT/'imports', help='Collector imports (read only)')
    ap.add_argument('--history', type=Path, default=ranking_history.FOLDER)
    ap.add_argument('--cache', type=Path, required=True, help='Response cache (use a separate one while the collector runs)')
    ap.add_argument('--category', action='append', required=True, help='TTScore ranking category id: 15 men, 10 women, ...')
    ap.add_argument('--since', default='', help='Earliest snapshot date to add (YYYY-MM-DD)')
    ap.add_argument('--limit', type=int, help='Stop after this many snapshots (probe)')
    ap.add_argument('--delay', type=float, default=3, help='Seconds between network requests')
    ap.add_argument('--offline', action='store_true')
    args = ap.parse_args()

    catalog = build(args.imports, ROOT/'data'/'verified_events.json')
    manifest_path = args.history/'provenance.json'
    manifest = (json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists()
                else {'adapter': ADAPTER, 'coverage': {'rankings': []}, 'requests': {}, 'csv_sha256': {}})
    have = {(r['category'], r['date']) for r in catalog['meta']['provenance']['coverage']['rankings']+manifest['coverage']['rankings']}
    client = Client(args.cache, args.offline, args.delay)
    selector, _ = client.get('/customer_ranking.php?customer=24')
    names = dict(options(selector, 'agecategoryid'))
    unknown = [c for c in args.category if c not in names]
    if unknown:
        raise SystemExit(f'Unknown ranking categories: {unknown}')
    # The newest snapshot is offered only as "latest" (value 0); its label carries the date.
    dates = sorted((re.search(r'\d{4}-\d{2}-\d{2}', label)[0], 'latest' if value == '0' else value)
                   for value, label in options(selector, 'select-date'))
    todo = [(c, d, request) for d, request in dates for c in args.category if d >= args.since and (names[c], d) not in have]
    if args.limit is not None:
        todo = todo[:args.limit]
    print(f'{len(todo)} snapshots to add', flush=True)

    rankings, players, coverage, rejected = {}, {}, [], []
    known_clubs = {c['id'] for c in catalog['clubs']}
    for category, date, request in todo:
        snapshot = Importer(client)  # isolated, so a rejected snapshot leaves nothing behind
        try:
            snapshot.ranking(category, request)
        except DataError as exc:
            rejected.append({'category': names[category], 'date': date, 'reason': str(exc)})
            print('Rejected', names[category], date, exc, flush=True)
            continue
        if set(snapshot.data['clubs']) - known_clubs:  # the collector owns club identities
            rejected.append({'category': names[category], 'date': date, 'reason': 'club not in the collector catalog'})
            print('Rejected', names[category], date, 'unknown club', flush=True)
            continue
        rankings.update(snapshot.data['rankings'])
        for ident, row in snapshot.data['players'].items():
            players[ident] = merge_player(players[ident], row) if ident in players else row
        coverage += snapshot.coverage['rankings']
        print('Added', names[category], date, snapshot.coverage['rankings'][-1]['rows'], flush=True)

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        if args.history.exists():
            for path in args.history.iterdir():
                if path.is_file():
                    shutil.copy2(path, staging/path.name)
        shards = {}
        for row in rankings.values():
            shards.setdefault(ranking_history.shard_name(row['date']), []).append(row)
        for name, rows in sorted(shards.items()):
            write_rows(staging/name, ranking_history.COLUMNS, read_rows(staging/name)+rows)
        existing = read_rows(staging/'players.csv')
        known = {p['id'] for p in catalog['players']} | {p['id'] for p in existing}
        added = [p for i, p in players.items() if i not in known]
        if added or not (staging/'players.csv').exists():
            write_rows(staging/'players.csv', ranking_history.PLAYER_COLUMNS, existing+added)
        manifest['adapter'] = ADAPTER
        manifest['requests'].update(client.records)
        manifest['coverage']['rankings'] = sorted(manifest['coverage']['rankings']+coverage, key=lambda r: (r['date'], r['category']))
        if rejected or manifest['coverage'].get('ranking_rejections'):
            manifest['coverage']['ranking_rejections'] = sorted(manifest['coverage'].get('ranking_rejections', [])+rejected,
                                                                key=lambda r: (r['date'], r['category']))
        manifest['csv_sha256'] = {p.name: digest(p.read_bytes()) for p in sorted(staging.glob('*.csv'))}
        (staging/'provenance.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')
        ranking_history.load(staging, catalog)  # validate the whole folder before replacing anything
        args.history.mkdir(parents=True, exist_ok=True)
        for path in sorted(staging.iterdir()):
            target = args.history/path.name
            if not target.exists() or target.read_bytes() != path.read_bytes():
                temporary = target.with_name(target.name+'.tmp')
                temporary.write_bytes(path.read_bytes())
                temporary.replace(target)
    print(json.dumps({'snapshots_added': len(coverage), 'rejected': len(rejected), 'ranking_rows': len(rankings),
                      'players_added': len(added)}), flush=True)


if __name__ == '__main__':
    main()
