import copy
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import identity_corrections  # noqa: E402
from build import build_site  # noqa: E402
from import_csv import DataError  # noqa: E402

URL = 'https://app.ttscore.io/test'


def single(ident, first, second, winner, clubs=('c1', 'c2')):
    return {'id': ident, 'event_id': 'e1', 'date': '2026-01-01', 'player1_id': first, 'player2_id': second, 'winner_id': winner,
            'club1_id': clubs[0], 'club2_id': clubs[1], 'status': 'completed', 'source_url': URL}


def catalog():
    """Synthetic: httf-12340 is httf-1234 mistyped on one sheet; "C.L.U.B" is "CLUB" with dots."""
    return {
        'players': [{'id': 'httf-1234', 'name': 'ALPHA ONE', 'aliases': 'ONE ALPHA', 'club_id': 'c1'},
                    {'id': 'httf-12340', 'name': 'ALPHA ONE', 'aliases': 'A. ONE', 'club_id': 'c1x'},
                    {'id': 'httf-2000', 'name': 'BETA TWO', 'aliases': '', 'club_id': 'c2'},
                    {'id': 'httf-3000', 'name': 'GAMMA THREE', 'aliases': '', 'club_id': 'c2'}],
        'clubs': [{'id': 'c1', 'name': 'CLUB'}, {'id': 'c1x', 'name': 'C.L.U.B'}, {'id': 'c2', 'name': 'OTHER'}],
        'matches': [single('m1', 'httf-1234', 'httf-2000', 'httf-1234'),
                    single('m2', 'httf-2000', 'httf-12340', 'httf-12340', clubs=('c2', 'c1x'))],
        'doubles': [{'id': 'd1', 'event_id': 'e1', 'player1_id': 'httf-12340', 'partner1_id': 'httf-3000',
                     'player2_id': 'httf-2000', 'partner2_id': ''}],
        'fixtures': [{'id': 'f1', 'event_id': 'e1', 'home_club_id': 'c1x', 'away_club_id': 'c2'}],
        'rankings': [{'id': 'r1', 'player_id': 'httf-1234', 'category': 'Men', 'date': '2026-01-01', 'rank': 1,
                      'points': 10.0, 'club_id': 'c1x', 'source_url': URL}],
        'standings': [{'id': 's1', 'event_id': 'e1', 'group_id': '1', 'club_id': 'c1x', 'club_name': 'C.L.U.B'}],
        'meta': {'inputs': [{'path': 'imports/players.csv', 'sha256': 'x'}]}}


def entry(source, target, source_name, target_name, basis):
    return {'from': source, 'to': target, 'from_name': source_name, 'to_name': target_name, 'basis': basis, 'evidence': 'Synthetic test evidence.'}


PLAYER = entry('httf-12340', 'httf-1234', 'ALPHA ONE', 'ALPHA ONE', 'registration_number_out_of_range')
CLUB = entry('c1x', 'c1', 'C.L.U.B', 'CLUB', 'same_name_different_punctuation')


def table(players=(PLAYER,), clubs=(CLUB,), **extra):
    return {'version': 1, 'players': list(players), 'clubs': list(clubs), **extra}


class IdentityCorrectionTests(unittest.TestCase):
    def load(self, value, data=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'identity-corrections.json'
            path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
            return identity_corrections.load(path, data or catalog())

    def refused(self, message, value, data=None):
        with self.assertRaisesRegex(DataError, message):
            self.load(value, data)

    def test_a_missing_table_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(identity_corrections.load(Path(tmp)/'identity-corrections.json', catalog()))
        data = catalog()
        self.assertEqual(identity_corrections.apply(data, None), catalog())

    def test_merged_identities_are_rewritten_in_every_table(self):
        data = catalog()
        identity_corrections.apply(data, self.load(table(), data))
        self.assertEqual([p['id'] for p in data['players']], ['httf-1234', 'httf-2000', 'httf-3000'])
        self.assertEqual([c['id'] for c in data['clubs']], ['c1', 'c2'])
        kept = data['players'][0]
        # Every other spelling becomes an alias; the display name is never its own alias.
        self.assertEqual((kept['name'], kept['aliases'], kept['club_id']), ('ALPHA ONE', 'A. ONE|ONE ALPHA', 'c1'))
        self.assertEqual(data['clubs'][0], {'id': 'c1', 'name': 'CLUB', 'aliases': 'C.L.U.B'})
        second = data['matches'][1]
        self.assertEqual((second['player2_id'], second['winner_id'], second['club2_id']), ('httf-1234', 'httf-1234', 'c1'))
        self.assertEqual(data['doubles'][0]['player1_id'], 'httf-1234')
        self.assertEqual(data['doubles'][0]['partner2_id'], '')  # an unresolved member stays empty
        self.assertEqual(data['fixtures'][0]['home_club_id'], 'c1')
        self.assertEqual(data['rankings'][0]['club_id'], 'c1')
        # The standings row keeps the source's own label; only the link to the club changes.
        self.assertEqual((data['standings'][0]['club_id'], data['standings'][0]['club_name']), ('c1', 'C.L.U.B'))
        meta = data['meta']
        self.assertEqual(meta['identity_corrections']['players'], {'httf-12340': 'httf-1234'})
        self.assertEqual(meta['identity_corrections']['clubs'], {'c1x': 'c1'})
        self.assertEqual([i['path'] for i in meta['inputs']], ['imports/players.csv', 'data/identity-corrections.json'])
        self.assertEqual(meta['inputs'][1]['sha256'], meta['identity_corrections']['sha256'])

    def test_malformed_tables_are_refused(self):
        self.refused('version 1', {'version': 2, 'players': []})
        self.refused('must be a list', {'version': 1, 'players': {}})
        self.refused('needs from, to', table(players=[{**PLAYER, 'evidence': ' '}]))
        self.refused('unknown basis', table(players=[{**PLAYER, 'basis': 'same_name'}]))
        self.refused('merged once', table(players=[PLAYER, PLAYER]))
        self.refused('is not in the catalog', table(players=[{**PLAYER, 'from': 'httf-9'}]))
        self.refused('both merged away and kept', table(players=[PLAYER, entry('httf-1234', 'httf-3000', 'ALPHA ONE', 'GAMMA THREE', 'reviewed_same_athlete')]))

    def test_an_entry_is_refused_when_the_catalog_no_longer_matches_it(self):
        renamed = catalog()
        renamed['players'][1]['name'] = 'SOMEONE ELSE'
        self.refused("now named 'SOMEONE ELSE'", table(), renamed)

    def test_an_entry_is_refused_when_the_catalog_contradicts_it(self):
        met = catalog()
        met['matches'].append(single('m3', 'httf-1234', 'httf-12340', 'httf-1234'))
        self.refused('match m3 is between two identities listed as one athlete', table(), met)
        paired = catalog()
        paired['doubles'][0]['partner1_id'] = 'httf-1234'
        self.refused('doubles d1 holds two identities', table(), paired)
        ranked = catalog()
        ranked['rankings'].append({**ranked['rankings'][0], 'id': 'r2', 'player_id': 'httf-12340'})
        self.refused('httf-12340 holds an official ranking', table(), ranked)
        derby = catalog()
        derby['fixtures'].append({'id': 'f2', 'event_id': 'e1', 'home_club_id': 'c1', 'away_club_id': 'c1x'})
        self.refused('fixture f2 is between two identities listed as one club', table(), derby)

    def test_athletes_reviewed_as_different_people_cannot_be_merged(self):
        distinct = [{'ids': ['httf-1234', 'httf-12340'], 'name': 'ALPHA ONE', 'evidence': 'Synthetic.'}]
        self.refused('were reviewed as different athletes', table(distinct=distinct))
        self.refused('needs two ids and evidence', table(distinct=[{'ids': ['httf-1234'], 'evidence': 'Synthetic.'}]))
        apart = [{'ids': ['httf-2000', 'httf-3000'], 'name': 'x', 'evidence': 'Synthetic.'}]
        self.assertEqual(self.load(table(distinct=apart))['players'], {'httf-12340': 'httf-1234'})

    def test_the_site_is_built_from_corrected_identities(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'data').mkdir()
            shutil.copytree(Path(__file__).resolve().parents[1]/'src', root/'src')
            (root/'data'/'catalog.json').write_text(json.dumps(catalog()))
            before = build_site(root)
            (root/'data'/'identity-corrections.json').write_text(json.dumps(table()))
            portable = build_site(root)
            self.assertNotEqual(before, portable)
            read = lambda page: json.loads(re.search(r'id="site-data">(.*?)</script>', page, re.S)[1])
            hosted = read((root/'dist'/'index.html').read_text())
            self.assertEqual(sorted(hosted['meta']['partitions']['player']), ['httf-1234', 'httf-2000', 'httf-3000'])
            self.assertEqual(sorted(hosted['meta']['partitions']['club']), ['c1', 'c2'])
            self.assertEqual(hosted['meta']['player_summary']['httf-1234'], [2, 2])  # both sheets count for one athlete
            self.assertEqual(hosted['meta']['identity_corrections']['players'], {'httf-12340': 'httf-1234'})
            own = json.loads((root/'dist'/hosted['meta']['partitions']['player']['httf-1234']).read_text())
            self.assertEqual([m['id'] for m in own['matches']], ['m1', 'm2'])
            self.assertEqual(json.loads((root/'dist'/'identity-corrections.json').read_text()), table())
            self.assertEqual(read(portable)['meta']['identity_corrections'], hosted['meta']['identity_corrections'])
            self.assertEqual(portable, build_site(root))


class SlimHostedPageTests(unittest.TestCase):
    def test_the_hosted_page_leaves_out_audit_fields_that_stay_downloadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'data').mkdir()
            shutil.copytree(Path(__file__).resolve().parents[1]/'src', root/'src')
            coverage = {'issues': [{'reason': 'unique-issue-marker'}], 'events': {'7': {'issues': 3, 'adapter_sha256': 'unique-adapter-marker', 'phases': ['league']}},
                        'batch': {'attempted': 1, 'processed_order': ['unique-order-marker']},
                        'rankings': [{'category': 'Men', 'date': '2026-01-01', 'rows': 1, 'source_id': 'unique-ranking-marker'}]}
            data = {'players': [{'id': 'p1', 'name': 'ALPHA ONE', 'identity_basis': 'federation_registration', 'source_id': 'unique-player-marker'}],
                    'events': [{'id': 'ttscore-7', 'name': 'League', 'season': '2025-26', 'source_url': URL, 'source_id': 'unique-event-marker'}],
                    'meta': {'provenance': {'requests': {}, 'coverage': copy.deepcopy(coverage)}}}
            (root/'data'/'catalog.json').write_text(json.dumps(data))
            portable = build_site(root)
            hosted_page = (root/'dist'/'index.html').read_text()
            for marker in ('issue', 'adapter', 'order', 'ranking', 'player', 'event'):
                self.assertNotIn(f'unique-{marker}-marker', hosted_page, marker)
                self.assertIn(f'unique-{marker}-marker', portable, marker)  # the offline copy stays complete
            hosted = json.loads(re.search(r'id="site-data">(.*?)</script>', hosted_page, re.S)[1])
            self.assertEqual(hosted['players'], [{'id': 'p1', 'name': 'ALPHA ONE'}])
            kept = hosted['meta']['provenance']['coverage']
            self.assertEqual(kept['events'], {'7': {'issues': 3, 'phases': ['league']}})  # the count stays, the list goes
            self.assertEqual(kept['batch'], {'attempted': 1})
            self.assertEqual(kept['rankings'], [{'category': 'Men', 'date': '2026-01-01', 'rows': 1}])
            self.assertEqual(json.loads((root/'dist'/'coverage.json').read_text()), coverage)


if __name__ == '__main__':
    unittest.main()
