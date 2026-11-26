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
EXCEPTIONS = ROOT/'data'/'ranking-source-exceptions.json'


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


def superseded_latest(manifest, dates):
    """Held snapshots that cite the "latest" request although the source now lists their date.

    The newest snapshot can only be requested as "latest" (select-date=0). Once a newer
    one is published, that same request returns the newer snapshot, so a row citing it
    would point at a response that no longer holds it.
    """
    listed = {date for date, request in dates if request != 'latest'}
    def form(key):
        return (manifest['requests'].get(key) or {}).get('request', {}).get('form') or {}
    return [held for held in manifest['coverage']['rankings']
            if held['date'] in listed and form(held['source_id']).get('select-date') == '0']


def comparable(rows, masked=frozenset()):
    """Rows as published, for comparison; the club of a row in masked is left out."""
    return sorted(tuple('' if k == 'club_id' and row['id'] in masked else row[k]
                        for k in ranking_history.COLUMNS if k != 'source_id') for row in rows)


def load_exceptions(path):
    """Reviewed source errors in the ranking lists, keyed by (athlete, club as the source shows it).

    data/ranking-source-exceptions.json lists clubs the source shows for an athlete that a
    person reviewed and found to be wrong, with the evidence. Where the source shows exactly
    that club for that athlete, the row is published without a club, and the provenance
    records it. Once the source corrects it, the entry no longer matches and does nothing.
    """
    if not path.exists():
        return {}
    spec = json.loads(path.read_text(encoding='utf-8'))
    if spec.get('version') != 1 or set(spec) - {'version', 'note', 'clubs'}:
        raise DataError(f'{path.name}: unsupported format')
    result = {}
    for entry in spec.get('clubs', []):
        fields = ('player_id', 'source_club', 'reviewed', 'evidence')
        if set(entry) != set(fields) or not all(isinstance(entry[f], str) and entry[f].strip() for f in fields):
            raise DataError(f'{path.name}: each club entry needs exactly {", ".join(fields)}')
        if (entry['player_id'], entry['source_club']) in result:
            raise DataError(f"{path.name}: {entry['player_id']} listed twice for {entry['source_club']!r}")
        result[(entry['player_id'], entry['source_club'])] = entry
    return result


def read_snapshot(client, category, request, exceptions):
    """One ranking snapshot with reviewed source errors applied: the importer and what was applied."""
    snapshot = Importer(client)
    snapshot.ranking(category, request)
    clubs, applied = snapshot.data['clubs'], []
    for row in snapshot.data['rankings'].values():
        shown = clubs.get(row['club_id'], {}).get('name', '')
        if (row['player_id'], shown) in exceptions:
            applied.append({'category': row['category'], 'date': row['date'], 'player_id': row['player_id'],
                            'row': row['id'], 'source_club': shown, 'published_club_id': ''})
            row['club_id'] = ''
    if applied:
        used = {row['club_id'] for row in snapshot.data['rankings'].values()}
        for ident in [c for c in clubs if c not in used]:
            del clubs[ident]
        for player in snapshot.data['players'].values():
            if player.get('club_id') and player['club_id'] not in clubs:
                player.update(club_id='', club_as_of='')
    return snapshot, applied


def recite(folder, moved):
    """Point rows of a superseded snapshot, and players first seen in it, at its dated request.

    moved maps (old source_id, category, date) to the new source_id.
    """
    by_key = {}
    for (old, _, _), new in moved.items():
        if by_key.setdefault(old, new) != new:
            raise DataError(f'Request {old[:12]} was cited by several snapshots; review by hand')
    for path in sorted(folder.glob('*.csv')):
        rows = read_rows(path)
        if path.name == 'players.csv':
            columns, target = ranking_history.PLAYER_COLUMNS, lambda r: by_key.get(r['source_id'])
        else:
            columns, target = ranking_history.COLUMNS, lambda r: moved.get((r['source_id'], r['category'], r['date']))
        if any(target(r) for r in rows):
            write_rows(path, columns, [{**r, 'source_id': target(r) or r['source_id']} for r in rows])


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
    ap.add_argument('--exceptions', type=Path, default=EXCEPTIONS, help='Reviewed source errors (default: %(default)s)')
    ap.add_argument('--replace', action='append', default=[], metavar='CATEGORY:DATE',
                    help='Read a held history snapshot again and replace it whole, after the source corrected it '
                         '(e.g. 15:2026-10-30; the category must also be given with --category)')
    args = ap.parse_args()

    catalog = build(args.imports, ROOT/'data'/'verified_events.json')
    exceptions = load_exceptions(args.exceptions)
    manifest_path = args.history/'provenance.json'
    manifest = (json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists()
                else {'adapter': ADAPTER, 'coverage': {'rankings': []}, 'requests': {}, 'csv_sha256': {}})
    client = Client(args.cache, args.offline, args.delay)
    selector, _ = client.get('/customer_ranking.php?customer=24')
    names = dict(options(selector, 'agecategoryid'))
    unknown = [c for c in args.category if c not in names]
    if unknown:
        raise SystemExit(f'Unknown ranking categories: {unknown}')
    # The newest snapshot is offered only as "latest" (value 0); its label carries the date.
    dates = sorted((re.search(r'\d{4}-\d{2}-\d{2}', label)[0], 'latest' if value == '0' else value)
                   for value, label in options(selector, 'select-date'))
    # A held snapshot the source has corrected since is read again and replaced whole.
    replaced = {}
    for item in args.replace:
        category, _, date = item.partition(':')
        if category not in args.category:
            raise SystemExit(f'--replace {item}: pass --category {category} as well')
        held = [s for s in manifest['coverage']['rankings'] if s['category'] == names[category] and s['date'] == date]
        if len(held) != 1:
            raise SystemExit(f'--replace {item}: {args.history} holds no {names[category]} snapshot of {date}')
        replaced[(names[category], date)] = held[0]
    manifest['coverage']['rankings'] = [s for s in manifest['coverage']['rankings'] if (s['category'], s['date']) not in replaced]
    have = {(r['category'], r['date']) for r in catalog['meta']['provenance']['coverage']['rankings']+manifest['coverage']['rankings']}
    # Before "latest" is asked for again: move held snapshots that cite it to their dated
    # request, after checking that the source still returns exactly the published rows.
    # Only the categories asked for now: "latest" is requested again for those alone.
    # A reviewed source error found in a dated list is not a change: the published row keeps
    # the club from the earlier retrieval, and the exception record says where it came from.
    moved, ids, applied = {}, {label: value for value, label in names.items()}, []
    for held in superseded_latest(manifest, dates):
        if ids.get(held['category']) not in args.category:
            continue
        try:
            snapshot, found = read_snapshot(client, ids[held['category']], held['date'], exceptions)
        except (DataError, KeyError) as exc:
            raise SystemExit(f"Could not read the {held['category']} ranking of {held['date']} by its date: {exc}")
        published = [r for r in read_rows(args.history/ranking_history.shard_name(held['date']))
                     if r['category'] == held['category'] and r['date'] == held['date'] and r['source_id'] == held['source_id']]
        masked = {item['row'] for item in found}
        if comparable(published, masked) != comparable(snapshot.data['rankings'].values(), masked):
            raise SystemExit(f"The {held['category']} ranking of {held['date']} no longer matches the published rows; "
                             'nothing was written, review before importing')
        earlier = manifest['requests'].get(held['source_id'], {})
        kept = {r['id']: r['club_id'] for r in published}
        applied += [{**item, 'published_club_id': kept[item['row']],
                     'published_club_from': {k: earlier.get(k) for k in ('retrieved_at', 'sha256')}} for item in found]
        new_key = snapshot.coverage['rankings'][-1]['source_id']
        moved[(held['source_id'], held['category'], held['date'])] = new_key
        held['source_id'] = new_key
        print('Re-cited', held['category'], held['date'], 'to its dated request', flush=True)
    todo = [(c, d, request) for d, request in dates for c in args.category
            if (d >= args.since or (names[c], d) in replaced) and (names[c], d) not in have]
    if args.limit is not None:
        todo = todo[:args.limit]
    print(f'{len(todo)} snapshots to add', flush=True)

    rankings, players, coverage, rejected = {}, {}, [], []
    known_clubs = {c['id'] for c in catalog['clubs']}
    for category, date, request in todo:
        try:  # each snapshot is isolated, so a rejected one leaves nothing behind
            snapshot, found = read_snapshot(client, category, request, exceptions)
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
        applied += found
        print('Added', names[category], date, snapshot.coverage['rankings'][-1]['rows'], flush=True)

    unread = sorted(set(replaced)-{(c['category'], c['date']) for c in coverage})
    if unread:
        raise SystemExit(f'Could not read {unread[0][0]} {unread[0][1]} again to replace it; nothing was written')

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        if args.history.exists():
            for path in args.history.iterdir():
                if path.is_file():
                    shutil.copy2(path, staging/path.name)
        recite(staging, moved)  # before new rows, which may cite the "latest" request again
        for (category, date), held in sorted(replaced.items()):
            path = staging/ranking_history.shard_name(date)
            rows = read_rows(path)
            old = {r['id']: r for r in rows if (r['category'], r['date']) == (category, date)}
            new = {i: r for i, r in rankings.items() if (r['category'], r['date']) == (category, date)}
            write_rows(path, ranking_history.COLUMNS, [r for r in rows if r['id'] not in old])
            # A player first seen in the old snapshot must still be in the response its row cites.
            lost = [p['id'] for p in read_rows(staging/'players.csv') if p['source_id'] == held['source_id']
                    and held['source_id'] in client.records and p['id'] not in {r['player_id'] for r in new.values()}]
            if lost:
                raise SystemExit(f'Replacing {category} {date} would leave {lost[0]} citing a response without them; nothing was written')
            fields = [c for c in ranking_history.COLUMNS if c not in ('id', 'source_id')]
            changed = sum(any(old[i][c] != new[i][c] for c in fields) for i in set(old) & set(new))
            print(f'Replaced {category} {date}: {len(old)} -> {len(new)} rows, {len(set(new)-set(old))} added, '
                  f'{len(set(old)-set(new))} removed, {changed} changed', flush=True)
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
        if applied or manifest['coverage'].get('source_exceptions'):
            redone = {(c['category'], c['date']) for c in coverage} | {(c, d) for _, c, d in moved}
            kept = [e for e in manifest['coverage'].get('source_exceptions', []) if (e['category'], e['date']) not in redone]
            manifest['coverage']['source_exceptions'] = sorted(kept+applied, key=lambda e: (e['date'], e['category'], e['row']))
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
                      'players_added': len(added), 're_cited': len(moved), 'replaced': len(replaced), 'exceptions_applied': len(applied)}), flush=True)


if __name__ == '__main__':
    main()
