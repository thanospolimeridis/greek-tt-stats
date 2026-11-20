import copy
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import ranking_history  # noqa: E402
from build import build_site, pack_rankings  # noqa: E402
from import_csv import DataError  # noqa: E402

URL = 'https://app.ttscore.io/customer_ranking.php?customer=24'


def ranking(player, category, date, rank, points, source='s1', club='c1'):
    return {'id': f'httf-ranking-{date}-{category}-{player}', 'player_id': player, 'category': category, 'date': date,
            'rank': rank, 'source_url': URL, 'club_id': club, 'points': points, 'source_id': source}


def catalog():
    # Synthetic catalog shaped like import_csv.build() output.
    return {'players': [{'id': 'p1', 'name': 'One', 'aliases': '', 'club_id': 'c1', 'source_id': 'b'}],
            'clubs': [{'id': 'c1', 'name': 'Club'}],
            'rankings': [ranking('p1', 'Men', '2026-10-01', 5, 900.0, source='b')],
            'meta': {'provenance': {'coverage': {'rankings': [{'category': 'Men', 'date': '2026-10-01', 'rows': 1}]}}}}


def write_history(folder, rows, players=(), requests=('s1',), tamper=None):
    folder.mkdir(parents=True, exist_ok=True)
    shards = {}
    for row in rows:
        shards.setdefault(ranking_history.shard_name(row['date']), []).append(row)
    for name, items in shards.items():
        with (folder/name).open('w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=ranking_history.COLUMNS)
            w.writeheader()
            w.writerows({k: ('' if v is None else v) for k, v in r.items()} for r in items)
    with (folder/'players.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=ranking_history.PLAYER_COLUMNS)
        w.writeheader()
        w.writerows(players)
    if tamper:
        tamper(folder)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.csv'))}
    coverage = sorted({(r['category'], r['date']) for r in rows})
    manifest = {'adapter': 'test', 'csv_sha256': hashes, 'requests': {k: {} for k in requests},
                'coverage': {'rankings': [{'category': c, 'date': d, 'rows': 1} for c, d in coverage]}}
    (folder/'provenance.json').write_text(json.dumps(manifest))


class RankingHistoryTests(unittest.TestCase):
    def load(self, rows, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'ranking-history'
            write_history(folder, rows, **kwargs)
            return ranking_history.load(folder, catalog())

    def assertRejects(self, message, rows, **kwargs):
        with self.assertRaisesRegex(DataError, message):
            self.load(rows, **kwargs)

    def test_missing_folder_means_no_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(ranking_history.load(Path(tmp)/'absent', catalog()))

    def test_valid_history_merges_deterministically_without_touching_base_provenance(self):
        rows = [ranking('p1', 'Men', '2025-01-01', 7, 850.5), ranking('p2', 'Boys', '2025-01-01', 1, 850.5)]
        newcomer = {'id': 'p2', 'name': 'Two', 'aliases': '', 'club_as_of': '2025-01-01', 'club_id': 'c1',
                    'identity_basis': 'federation_registration', 'source_id': 's1'}
        history = self.load(rows, players=[newcomer])
        self.assertEqual(sorted(r['rank'] for r in history['rankings']), [1, 7])
        self.assertEqual(history['rankings'][0]['points'], 850.5)
        base = catalog()
        original_coverage = copy.deepcopy(base['meta']['provenance']['coverage'])
        coverage_object = base['meta']['provenance']['coverage']
        merged = ranking_history.merge(base, history)
        self.assertEqual([p['id'] for p in merged['players']], ['p1', 'p2'])
        self.assertEqual([r['id'] for r in merged['rankings']], sorted(r['id'] for r in merged['rankings']))
        self.assertEqual(len(merged['meta']['provenance']['coverage']['rankings']), 3)
        self.assertEqual(coverage_object, original_coverage)
        again = ranking_history.merge(catalog(), self.load(rows, players=[newcomer]))
        self.assertEqual(json.dumps(merged, sort_keys=True), json.dumps(again, sort_keys=True))

    def test_catalog_player_wins_over_history_player(self):
        duplicate = {'id': 'p1', 'name': 'Other name', 'aliases': '', 'club_as_of': '', 'club_id': '',
                     'identity_basis': 'federation_registration', 'source_id': 's1'}
        history = self.load([ranking('p1', 'Men', '2025-01-01', 7, 1.0)], players=[duplicate])
        self.assertEqual(history['players'], [])

    def test_hash_mismatch(self):
        rows = [ranking('p1', 'Men', '2025-01-01', 7, 1.0)]
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'ranking-history'
            write_history(folder, rows)
            with (folder/'rankings-2025.csv').open('a', encoding='utf-8') as f:
                f.write('\n')
            with self.assertRaisesRegex(DataError, 'hashes do not match'):
                ranking_history.load(folder, catalog())

    def test_unknown_source(self):
        self.assertRejects('unknown provenance', [ranking('p1', 'Men', '2025-01-01', 7, 1.0, source='zz')])

    def test_unknown_player(self):
        self.assertRejects('unknown player', [ranking('p9', 'Men', '2025-01-01', 7, 1.0)])

    def test_unknown_club(self):
        self.assertRejects('unknown club', [ranking('p1', 'Men', '2025-01-01', 7, 1.0, club='c9')])

    def test_duplicate_of_catalog_snapshot(self):
        self.assertRejects('duplicate', [ranking('p1', 'Men', '2026-10-01', 7, 1.0)])

    def test_invalid_rank_and_points(self):
        self.assertRejects('rank must be', [ranking('p1', 'Men', '2025-01-01', 0, 1.0)])
        self.assertRejects('points must be', [ranking('p1', 'Men', '2025-01-01', 3, -1)])
        self.assertRejects('invalid points', [ranking('p1', 'Men', '2025-01-01', 3, 'x')])

    def test_row_in_wrong_shard(self):
        def move(folder):
            (folder/'rankings-2025.csv').rename(folder/'rankings-2024.csv')
        self.assertRejects('belongs in rankings-2025.csv', [ranking('p1', 'Men', '2025-01-01', 7, 1.0)], tamper=move)


class PackTests(unittest.TestCase):
    def test_pack_stores_snapshot_fields_once(self):
        rows = [ranking('p1', 'Men', '2025-01-01', 1, 10.0), ranking('p2', 'Men', '2025-01-01', 2, 9.0, club=''),
                ranking('p1', 'Boys', '2025-01-01', 1, 10.0)]
        packed = pack_rankings(rows)
        self.assertEqual(packed['format'], 'ranking-snapshots-v1')
        self.assertEqual(packed['snapshots'], [['2025-01-01', 'Men', 's1', URL], ['2025-01-01', 'Boys', 's1', URL]])
        self.assertEqual(packed['clubs'], ['c1', ''])
        self.assertEqual(packed['rows'], [[0, 'p1', 1, 10.0, 0], [0, 'p2', 2, 9.0, 1], [1, 'p1', 1, 10.0, 0]])

    def test_build_merges_history_into_player_and_date_files_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'data').mkdir()
            shutil.copytree(Path(__file__).resolve().parents[1]/'src', root/'src')
            base = catalog()
            base.update(matches=[], doubles=[], fixtures=[], events=[])
            (root/'data'/'catalog.json').write_text(json.dumps(base))
            write_history(root/'imports'/'ranking-history', [ranking('p1', 'Men', '2025-01-01', 7, 1.0)])
            build_site(root)
            hosted = (root/'dist'/'index.html').read_text()
            payload = json.loads(re.search(r'id="site-data">(.*?)</script>', hosted, re.S)[1])
            self.assertEqual([s[0] for s in payload['rankings']['snapshots']], ['2026-10-01'])
            self.assertEqual(payload['meta']['table_counts']['rankings'], 2)
            self.assertEqual(payload['meta']['ranking_dates'], {'Men': ['2026-10-01', '2025-01-01']})
            player = json.loads((root/'dist'/payload['meta']['partitions']['player']['p1']).read_text())
            self.assertEqual(len(player['rankings']['rows']), 2)
            past = json.loads((root/'dist'/payload['meta']['partitions']['ranking']['2025-01-01']).read_text())
            self.assertEqual(past['rankings']['rows'], [[0, 'p1', 7, 1.0, 0]])
            self.assertTrue((root/'dist'/'ranking-history-provenance.json').exists())
            self.assertFalse((root/'ranking-history-provenance.json').exists())


if __name__ == '__main__':
    unittest.main()
