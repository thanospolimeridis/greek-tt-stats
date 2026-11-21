#!/usr/bin/env python3
"""Write the league standings TTScore publishes to imports/standings/.

For every league event in the collector's catalog this replays the two public
read-only requests the collector already makes (the league page, then one overview
per category) with the same client and cache format as ttscore.py, and keeps the
table each overview shows: Wins, Lost, Disq and Pts per team. Nothing is computed
from fixtures. The folder is rebuilt whole on every run, so a refresh replaces the
previous snapshot; the collector's imports are only read. A group whose table cannot
be read is left out and listed in coverage. Any HTTP or network failure stops the
run before anything is written. The result is validated with standings.load().

    python3 scripts/import_standings.py --cache capture/ttscore --offline   # from the collector's cache
    python3 scripts/import_standings.py --cache capture/ttscore-standings   # fresh retrieval, separate cache
"""
import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ttscore import BASE, ROOT, Client, DataError, SourceAccessError, digest, options  # noqa: E402
from import_csv import build  # noqa: E402
import standings  # noqa: E402

ADAPTER = 'ttscore-league-standings-v1'


def collect(client, events, clubs):
    """Rows, coverage and rejections for the given league event numbers."""
    rows, coverage, rejected = [], [], []
    for event in events:
        path = f'/tournament_groups_league.php?event={event}&customer=24'
        page, _ = client.get(path)
        for value, category in options(page, 'agecategoryid_league'):
            body, key = client.get('/tournament_groups_league.php',
                                   {'event': event, 'customer': '24', 'getStats': '1', 'agecategoryid_league': value})
            as_of = client.records[key]['retrieved_at'][:10]
            try:
                groups = standings.parse_groups(body)
            except SourceAccessError:
                raise
            except DataError as exc:
                rejected.append({'event': event, 'category': category, 'reason': str(exc), 'source_id': key})
                continue
            for group, table, placeholders in groups:
                coverage.append({'event': event, 'group': group, 'category': category, 'rows': len(table),
                                 'placeholders_skipped': placeholders, 'as_of': as_of, 'source_id': key})
                for row in table:
                    # Same identity rule as the collector: the exact source club name.
                    club = 'club-name-'+digest(row['club_name'].encode())[:16]
                    rows.append({**row, 'id': f"ttscore-standing-{group}-{row['slot']}", 'event_id': 'ttscore-'+event,
                                 'group_id': group, 'category': category, 'club_id': club if club in clubs else '',
                                 'as_of': as_of, 'source_id': key, 'source_url': BASE+path})
    return rows, coverage, rejected


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--imports', type=Path, default=ROOT/'imports', help='Collector imports (read only)')
    ap.add_argument('--output', type=Path, default=standings.FOLDER)
    ap.add_argument('--cache', type=Path, required=True, help='Response cache (use a separate one for fresh retrievals)')
    ap.add_argument('--event', action='append', help='League event number; default: every league in the catalog')
    ap.add_argument('--delay', type=float, default=3, help='Seconds between network requests')
    ap.add_argument('--offline', action='store_true')
    args = ap.parse_args()

    catalog = build(args.imports, ROOT/'data'/'verified_events.json')
    leagues = sorted(catalog['meta']['provenance']['coverage'].get('leagues', {}), key=int)
    unknown = sorted(set(args.event or [])-set(leagues))
    if unknown:
        raise SystemExit(f'Not league events in the catalog: {unknown}')
    client = Client(args.cache, args.offline, args.delay)
    rows, coverage, rejected = collect(client, args.event or leagues, {c['id'] for c in catalog['clubs']})
    order = lambda r: (int(r['event']), int(r['group']))  # noqa: E731
    manifest = {'adapter': ADAPTER, 'requests': dict(sorted(client.records.items())),
                'coverage': {'standings': sorted(coverage, key=order)}}
    if rejected:
        manifest['coverage']['standing_rejections'] = sorted(rejected, key=lambda r: (int(r['event']), r['category']))
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        with (staging/'standings.csv').open('w', encoding='utf-8', newline='') as target:
            writer = csv.DictWriter(target, fieldnames=standings.COLUMNS, extrasaction='raise')
            writer.writeheader()
            writer.writerows(sorted(rows, key=lambda r: (int(r['event_id'].removeprefix('ttscore-')), int(r['group_id']), r['slot'])))
        manifest['csv_sha256'] = {'standings.csv': digest((staging/'standings.csv').read_bytes())}
        (staging/'provenance.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')
        standings.load(staging, catalog)  # validate the whole folder before replacing anything
        args.output.mkdir(parents=True, exist_ok=True)
        for path in sorted(staging.iterdir()):
            target = args.output/path.name
            if not target.exists() or target.read_bytes() != path.read_bytes():
                temporary = target.with_name(target.name+'.tmp')
                temporary.write_bytes(path.read_bytes())
                temporary.replace(target)
    print(json.dumps({'events': len({c['event'] for c in coverage}), 'groups': len(coverage), 'rows': len(rows),
                      'placeholders_skipped': sum(c['placeholders_skipped'] for c in coverage), 'rejected': len(rejected)}), flush=True)


if __name__ == '__main__':
    main()
