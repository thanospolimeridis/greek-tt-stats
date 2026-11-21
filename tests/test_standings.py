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
import standings  # noqa: E402
from build import build_site  # noqa: E402
from import_csv import DataError  # noqa: E402
from import_standings import collect  # noqa: E402

URL = 'https://app.ttscore.io/tournament_groups_league.php?event=7&customer=24'
CLUB_A = 'club-name-'+hashlib.sha256('Club A'.encode()).hexdigest()[:16]


def table(group, lines, headers=standings.HEADERS):
    """Synthetic overview markup shaped like the source's league group table."""
    head = ''.join(f'<th width="5%">{h}</th>' for h in headers)
    body = ''.join(f'<tr class="pos-{c[0]}"><td class="">{c[0]}</td><td class="player">{c[1]}</td><td class="wins">{c[2]}</td>'
                   f'<td class="lost">{c[3]}</td><td class="disq">{c[4]}</td><td class="pts">{c[5]}</td></tr>' for c in lines)
    return (f'<div class="groups" id="grp-1" data-id="{group}"><table id="grpstatus-1"><caption> League '
            f"<button onclick=\"loadSchedule('{group}', '1')\">Results</button></caption>"
            f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


def standing(group, slot, points, club='Club A', team=None, club_id=CLUB_A, event='ttscore-7', source='s1', **extra):
    return {'id': f'ttscore-standing-{group}-{slot}', 'event_id': event, 'group_id': group, 'category': 'Men', 'slot': slot,
            'club_name': club, 'team_name': team or club, 'club_id': club_id, 'wins': 1, 'losses': 0, 'disqualified': 0,
            'points': points, 'as_of': '2026-11-20', 'source_id': source, 'source_url': URL, **extra}


def catalog():
    return {'events': [{'id': 'ttscore-7'}, {'id': 'ttscore-8'}], 'clubs': [{'id': CLUB_A, 'name': 'Club A'}],
            'players': [], 'rankings': [], 'matches': [], 'doubles': [], 'fixtures': [], 'meta': {}}


def write_folder(folder, rows, requests=('s1',), coverage=None):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder/'standings.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=standings.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    if coverage is None:
        counts = {}
        for r in rows:
            key = (r['event_id'].removeprefix('ttscore-'), r['group_id'])
            counts[key] = counts.get(key, 0)+1
        coverage = [{'event': e, 'group': g, 'rows': n} for (e, g), n in sorted(counts.items())]
    manifest = {'adapter': 'test', 'requests': {k: {} for k in requests}, 'coverage': {'standings': coverage},
                'csv_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.csv'))}}
    (folder/'provenance.json').write_text(json.dumps(manifest))


class ParseTests(unittest.TestCase):
    def test_rows_keep_the_source_numbers_and_split_club_from_team(self):
        body = table('55', [(1, 'Club A   - Club A', 8, 0, 0, 16), (2, 'Club B  - Club B &amp; Friends', 1, 7, 1, 8)])
        self.assertEqual(standings.parse_groups(body), [('55', [
            {'slot': 1, 'club_name': 'Club A', 'team_name': 'Club A', 'wins': 8, 'losses': 0, 'disqualified': 0, 'points': 16},
            {'slot': 2, 'club_name': 'Club B', 'team_name': 'Club B & Friends', 'wins': 1, 'losses': 7, 'disqualified': 1, 'points': 8}], 0)])

    def test_points_are_never_recomputed(self):
        # The source is not consistent about whether Disq is inside Lost; its Pts stand as published.
        rows = standings.parse_groups(table('55', [(1, 'Club A - Club A', 0, 0, 2, 0), (2, 'Club B - Club B', 1, 2, 1, 3)]))[0][1]
        self.assertEqual([r['points'] for r in rows], [0, 3])

    def test_empty_draw_slots_are_counted_not_listed(self):
        group, rows, placeholders = standings.parse_groups(table('55', [(1, 'Χ  - X - BYE', 0, 0, 0, 0), (2, 'Club A - Club A', 1, 0, 0, 2)]))[0]
        self.assertEqual(([r['club_name'] for r in rows], placeholders), (['Club A'], 1))

    def test_several_groups_in_one_response(self):
        body = table('55', [(1, 'Club A - Club A', 1, 0, 0, 2)])+table('56', [(1, 'Club B - Club B', 0, 1, 0, 1)])
        self.assertEqual([g for g, _, _ in standings.parse_groups(body)], ['55', '56'])
        self.assertEqual(standings.parse_groups('<p>No groups</p>'), [])

    def test_unexpected_markup_is_rejected(self):
        for message, body in (
                ('columns changed', table('55', [(1, 'Club A - Club A', 1, 0, 0, 2)], headers=['#', 'Participant', 'Wins', 'Lost', 'Pts'])),
                ('unexpected team label', table('55', [(1, 'Person A. - ', 3, 0, 0, 6)])),
                ('unexpected team label', table('55', [(1, 'Club - A - B', 3, 0, 0, 6)])),
                ('unreadable standings row', table('55', [(1, 'Club A - Club A', 'x', 0, 0, 6)])),
                ('repeated draw slot', table('55', [(1, 'Club A - Club A', 1, 0, 0, 2), (1, 'Club B - Club B', 0, 1, 0, 1)]))):
            with self.assertRaisesRegex(DataError, message):
                standings.parse_groups(body)


class Client:
    """Stands in for ttscore.Client: canned bodies keyed like the real requests."""
    def __init__(self, pages):
        self.pages, self.records = pages, {}

    def get(self, path, form=None):
        key = path if form is None else f"{form['event']}:{form['agecategoryid_league']}"
        self.records[key] = {'retrieved_at': '2026-11-20T23:41:33+00:00'}
        return self.pages[key], key


class CollectTests(unittest.TestCase):
    def test_collect_links_known_clubs_and_reports_unreadable_groups(self):
        selector = '<select name="agecategoryid_league"><option value="281">Men</option><option value="282">Women</option></select>'
        client = Client({'/tournament_groups_league.php?event=7&customer=24': selector,
                         '7:281': table('55', [(1, 'Club A - Club A', 2, 0, 0, 4), (2, 'Club Z - Club Z', 0, 2, 0, 2)]),
                         '7:282': table('56', [(1, 'Person A. - ', 1, 0, 0, 2)])})
        rows, coverage, rejected = collect(client, ['7'], {CLUB_A})
        self.assertEqual([(r['id'], r['club_id'], r['category'], r['as_of'], r['source_id']) for r in rows],
                         [('ttscore-standing-55-1', CLUB_A, 'Men', '2026-11-20', '7:281'), ('ttscore-standing-55-2', '', 'Men', '2026-11-20', '7:281')])
        self.assertEqual(rows[0]['source_url'], URL)
        self.assertEqual(coverage, [{'event': '7', 'group': '55', 'category': 'Men', 'rows': 2, 'placeholders_skipped': 0,
                                     'as_of': '2026-11-20', 'source_id': '7:281'}])
        self.assertEqual([(r['category'], r['source_id']) for r in rejected], [('Women', '7:282')])
        self.assertIn('unexpected team label', rejected[0]['reason'])


class LoadTests(unittest.TestCase):
    def load(self, rows, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'standings'
            write_folder(folder, rows, **kwargs)
            return standings.load(folder, catalog())

    def assertRejects(self, message, rows, **kwargs):
        with self.assertRaisesRegex(DataError, message):
            self.load(rows, **kwargs)

    def test_missing_folder_means_no_standings(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(standings.load(Path(tmp)/'absent', catalog()))

    def test_valid_table_merges_in_a_fixed_order_with_a_summary(self):
        rows = [standing('60', 1, 2, event='ttscore-8'), standing('55', 2, 4), standing('55', 1, 6)]
        merged = standings.merge(catalog(), self.load(rows))
        self.assertEqual([r['id'] for r in merged['standings']], ['ttscore-standing-55-1', 'ttscore-standing-55-2', 'ttscore-standing-60-1'])
        self.assertEqual((merged['standings'][0]['points'], merged['standings'][0]['slot']), (6, 1))
        summary = merged['meta']['league_standings']
        self.assertEqual((summary['rows'], summary['groups'], summary['events']), (3, 2, 2))
        self.assertEqual([i['path'] for i in merged['meta']['inputs']], ['imports/standings/standings.csv', 'imports/standings/provenance.json'])
        again = standings.merge(catalog(), self.load(rows))
        self.assertEqual(json.dumps(merged, sort_keys=True), json.dumps(again, sort_keys=True))

    def test_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'standings'
            write_folder(folder, [standing('55', 1, 6)])
            with (folder/'standings.csv').open('a', encoding='utf-8') as f:
                f.write('\n')
            with self.assertRaisesRegex(DataError, 'hash does not match'):
                standings.load(folder, catalog())

    def test_rows_must_belong_to_the_catalog_and_the_manifest(self):
        self.assertRejects('unknown event', [standing('55', 1, 6, event='ttscore-99')])
        self.assertRejects('unknown club', [standing('55', 1, 6, club_id='club-name-missing')])
        self.assertRejects('unknown provenance', [standing('55', 1, 6, source='zz')])
        self.assertRejects('unexpected source URL', [standing('55', 1, 6, source_url='https://example.com/x')])
        self.assertRejects('group belongs to another event', [standing('55', 1, 6), standing('55', 2, 4, event='ttscore-8')])
        self.assertRejects('do not match the coverage', [standing('55', 1, 6)], coverage=[{'event': '7', 'group': '55', 'rows': 2}])

    def test_malformed_rows(self):
        self.assertRejects('id does not match', [standing('55', 1, 6, id='ttscore-standing-55-9')])
        self.assertRejects('duplicate row', [standing('55', 1, 6), standing('55', 1, 6)])
        self.assertRejects('points', [standing('55', 1, -1)])
        self.assertRejects('wins', [standing('55', 1, 6, wins='many')])
        self.assertRejects('invalid retrieval date', [standing('55', 1, 6, as_of='yesterday')])
        self.assertRejects('missing team or category', [standing('55', 1, 6, category='')])

    def test_unlinked_club_is_allowed(self):
        self.assertEqual(self.load([standing('55', 1, 6, club='Club Z', club_id='')])['rows'][0]['club_id'], '')


class BuildTests(unittest.TestCase):
    def test_only_league_files_carry_standings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'data').mkdir()
            shutil.copytree(Path(__file__).resolve().parents[1]/'src', root/'src')
            base = catalog()
            base['fixtures'] = [{'id': 'f1', 'event_id': 'ttscore-8', 'home_club_id': CLUB_A, 'away_club_id': CLUB_A}]
            (root/'data'/'catalog.json').write_text(json.dumps(base))
            write_folder(root/'imports'/'standings', [standing('55', 1, 6), standing('55', 2, 4, club='Club Z', club_id='')])
            portable = build_site(root)
            hosted = (root/'dist'/'index.html').read_text()
            payload = json.loads(re.search(r'id="site-data">(.*?)</script>', hosted, re.S)[1])
            self.assertEqual(payload['standings'], [])
            self.assertEqual(payload['meta']['league_standings']['rows'], 2)
            league = json.loads((root/'dist'/payload['meta']['partitions']['event']['ttscore-7']).read_text())
            self.assertEqual([(r['club_name'], r['points']) for r in league['standings']], [('Club A', 6), ('Club Z', 4)])
            other = json.loads((root/'dist'/payload['meta']['partitions']['event']['ttscore-8']).read_text())
            self.assertNotIn('standings', other)
            offline = json.loads(re.search(r'id="site-data">(.*?)</script>', portable, re.S)[1])
            self.assertEqual(len(offline['standings']), 2)
            self.assertTrue((root/'dist'/'standings-provenance.json').exists())
            self.assertFalse((root/'standings-provenance.json').exists())
            self.assertEqual(portable, build_site(root))


if __name__ == '__main__':
    unittest.main()
