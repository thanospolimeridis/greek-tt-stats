#!/usr/bin/env python3
"""Add official TTScore ranking snapshots to an existing import.

Each snapshot is one public read-only request (category x date) fetched with the
same client, cache format and parser as ttscore.py. Rows are appended to
rankings.csv; only players and clubs that are not already present are added, so
existing rows and every results CSV stay byte-identical. provenance.json gains
the request records, one coverage entry per snapshot and refreshed CSV hashes.
A snapshot that fails validation is rejected whole and listed in coverage.
Any HTTP or network failure stops the run before anything is written.

    python3 scripts/import_rankings.py --cache capture/ttscore-rankings --category 15 --category 10
    python3 scripts/import_rankings.py ... --offline   # rebuild from the cache only
"""
import argparse
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ttscore import ROOT, Client, DataError, Importer, digest, options  # noqa: E402
from import_csv import build  # noqa: E402


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as source:
        reader = csv.DictReader(source)
        return list(reader.fieldnames), list(reader)


def write_csv(path, columns, rows):
    with path.open('w', encoding='utf-8', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def merge_player(old, new):
    """Same identity seen in several snapshots: keep the newest club, collect names."""
    base, other = (new, old) if new.get('club_as_of', '') >= old.get('club_as_of', '') else (old, new)
    names = set(filter(None, base.get('aliases', '').split('|') + other.get('aliases', '').split('|') + [other['name']]))
    return {**base, 'aliases': '|'.join(sorted(names - {base['name']}))}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--imports', type=Path, default=ROOT/'imports')
    ap.add_argument('--cache', type=Path, required=True, help='Response cache (use a separate one while the collector runs)')
    ap.add_argument('--category', action='append', required=True, help='TTScore ranking category id: 15 men, 10 women, ...')
    ap.add_argument('--since', default='', help='Earliest snapshot date to add (YYYY-MM-DD)')
    ap.add_argument('--limit', type=int, help='Stop after this many snapshots (probe)')
    ap.add_argument('--delay', type=float, default=3, help='Seconds between network requests')
    ap.add_argument('--offline', action='store_true')
    args = ap.parse_args()

    manifest = json.loads((args.imports/'provenance.json').read_text(encoding='utf-8'))
    have = {(r['category'], r['date']) for r in manifest['coverage']['rankings']}
    client = Client(args.cache, args.offline, args.delay)
    selector, _ = client.get('/customer_ranking.php?customer=24')
    names = dict(options(selector, 'agecategoryid'))
    unknown = [c for c in args.category if c not in names]
    if unknown:
        raise SystemExit(f'Unknown ranking categories: {unknown}')
    dates = sorted(v for v, _ in options(selector, 'select-date') if v != '0')
    todo = [(c, d) for d in dates for c in args.category if d >= args.since and (names[c], d) not in have]
    if args.limit is not None:
        todo = todo[:args.limit]
    print(f'{len(todo)} snapshots to add', flush=True)

    rankings, players, clubs, coverage, rejected = {}, {}, {}, [], []
    for category, date in todo:
        snapshot = Importer(client)  # isolated, so a rejected snapshot leaves nothing behind
        try:
            snapshot.ranking(category, date)
        except DataError as exc:
            rejected.append({'category': names[category], 'date': date, 'reason': str(exc)})
            print('Rejected', names[category], date, exc, flush=True)
            continue
        rankings.update(snapshot.data['rankings'])
        clubs.update(snapshot.data['clubs'])
        for ident, row in snapshot.data['players'].items():
            players[ident] = merge_player(players[ident], row) if ident in players else row
        coverage += snapshot.coverage['rankings']
        print('Added', names[category], date, snapshot.coverage['rankings'][-1]['rows'], flush=True)

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        for path in args.imports.iterdir():
            if path.is_file():
                shutil.copy2(path, staging/path.name)
        for kind, new_rows in (('rankings', rankings), ('players', players), ('clubs', clubs)):
            columns, rows = read_csv(staging/f'{kind}.csv')
            existing = {r['id'] for r in rows}
            added = [r for i, r in new_rows.items() if i not in existing]
            if not added:
                continue
            columns += sorted(set().union(*(set(r) for r in added)) - set(columns))
            write_csv(staging/f'{kind}.csv', columns, sorted(rows + added, key=lambda r: r['id']))
            print(f'{kind}: +{len(added)}', flush=True)
        manifest['requests'].update(client.records)
        manifest['coverage']['rankings'] = sorted(manifest['coverage']['rankings'] + coverage, key=lambda r: (r['date'], r['category']))
        if rejected:
            manifest['coverage']['ranking_rejections'] = sorted(manifest['coverage'].get('ranking_rejections', []) + rejected,
                                                                key=lambda r: (r['date'], r['category']))
        manifest['csv_sha256'] = {p.name: digest(p.read_bytes()) for p in sorted(staging.glob('*.csv'))}
        (staging/'provenance.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')
        build(staging, ROOT/'data'/'verified_events.json')  # validate the whole import before replacing anything
        for path in sorted(staging.iterdir()):
            target = args.imports/path.name
            if not target.exists() or target.read_bytes() != path.read_bytes():
                temporary = target.with_name(target.name+'.tmp')
                temporary.write_bytes(path.read_bytes())
                temporary.replace(target)
    print(json.dumps({'snapshots_added': len(coverage), 'rejected': len(rejected), 'ranking_rows': len(rankings)}), flush=True)


if __name__ == '__main__':
    main()
