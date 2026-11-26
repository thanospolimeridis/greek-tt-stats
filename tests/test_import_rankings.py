"""Adding ranking snapshots: a newer "latest" must not take over the request older rows cite (synthetic source only)."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import import_rankings  # noqa: E402
import ranking_history  # noqa: E402
from ttscore import BASE, Importer, digest  # noqa: E402

SELECTOR = ('<select name="agecategoryid"><option value="15">Men</option></select>'
            '<select name="select-date"><option value="0">{latest} Latest</option>{older}</select>')
CLUB = Importer(None).club('Club')


def table(rows):
    """Ranking rows as (rank, number, name, points[, club]); the club defaults to "Club"."""
    return '<table>'+''.join(f'<tr><td>{rank}</td><td></td><td>{number}</td><td>{name}</td><td>{(club or ["Club"])[0]}</td><td></td><td></td><td>{points}</td></tr>'
                             for rank, number, name, points, *club in rows)+'</table>'


def key(path, form=None):
    request = {'url': BASE+path, 'method': 'POST' if form is not None else 'GET', 'form': form}
    return digest(json.dumps(request, sort_keys=True).encode()), request


def ranking_form(date):
    return {'customer': '24', 'getStats': '1', 'select-date': date, 'agecategoryid': '15'}


class FakeSource:
    """Answers the two ranking requests from fixed pages and records them like Client does."""

    def __init__(self, pages):
        self.pages, self.records = pages, {}

    def get(self, path, form=None):
        ident, request = key(path, form)
        body = self.pages[ident]
        self.records[ident] = {'request': request, 'retrieved_at': '2026-11-24T08:00:00+00:00',
                               'sha256': digest(body.encode()), 'bytes': len(body), 'status': 200}
        return body, ident


OCTOBER = [(1, '101', 'One', '900.5'), (2, '102', 'Two', '800.0')]
LATEST, _ = key('/customer_ranking.php', ranking_form('0'))
DATED, _ = key('/customer_ranking.php', ranking_form('2026-10-01'))
SELECTOR_KEY, _ = key('/customer_ranking.php?customer=24')


def held(folder):
    """A history holding the 1 October snapshot as it was imported while it was "latest"."""
    folder.mkdir(parents=True)
    rows = [{'id': f'httf-ranking-2026-10-01-15-{n}', 'player_id': f'httf-{n}', 'category': 'Men', 'date': '2026-10-01',
             'rank': str(rank), 'source_url': BASE+'/customer_ranking.php?customer=24', 'club_id': CLUB, 'points': points,
             'source_id': LATEST} for rank, n, _, points in OCTOBER]
    import_rankings.write_rows(folder/'rankings-2026.csv', ranking_history.COLUMNS, rows)
    import_rankings.write_rows(folder/'players.csv', ranking_history.PLAYER_COLUMNS, [
        {'id': 'httf-102', 'name': 'Two', 'aliases': '', 'club_as_of': '2026-10-01', 'club_id': CLUB,
         'identity_basis': 'federation_registration', 'source_id': LATEST}])
    _, request = key('/customer_ranking.php', ranking_form('0'))
    manifest = {'adapter': import_rankings.ADAPTER,
                'requests': {LATEST: {'request': request, 'retrieved_at': '2026-11-20T10:00:00+00:00', 'sha256': 'old'}},
                'coverage': {'rankings': [{'category': 'Men', 'date': '2026-10-01', 'rows': 2, 'source_id': LATEST}]},
                'csv_sha256': {p.name: digest(p.read_bytes()) for p in sorted(folder.glob('*.csv'))}}
    (folder/'provenance.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)+'\n')


CATALOG = {'players': [{'id': 'httf-101', 'name': 'One', 'aliases': '', 'club_id': CLUB, 'source_id': 'b'}],
           'clubs': [{'id': CLUB, 'name': 'Club'}], 'rankings': [],
           'meta': {'provenance': {'coverage': {'rankings': []}}}}


class LatestSnapshotTests(unittest.TestCase):
    def run_import(self, folder, pages):
        source = FakeSource(pages)
        argv = ['import_rankings.py', '--imports', str(folder.parent), '--history', str(folder), '--cache', str(folder.parent/'cache'),
                '--category', '15', '--since', '2026-10-01']
        with patch.object(sys, 'argv', argv), patch.object(import_rankings, 'build', lambda *a: CATALOG), \
                patch.object(import_rankings, 'Client', lambda *a: source), patch('builtins.print'):
            import_rankings.main()
        return source

    def pages(self, dated_rows):
        return {SELECTOR_KEY: SELECTOR.format(latest='2026-10-30', older='<option value="2026-10-01">2026-10-01</option>'),
                LATEST: table([(1, '102', 'Two', '950.0'), (2, '101', 'One', '910.0')]),
                DATED: table(dated_rows)}

    def test_a_newer_latest_moves_the_older_snapshot_to_its_dated_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'ranking-history'
            held(folder)
            source = self.run_import(folder, self.pages(OCTOBER))
            manifest = json.loads((folder/'provenance.json').read_text())
            with (folder/'rankings-2026.csv').open(encoding='utf-8', newline='') as f:
                cites = {(r['date'], r['player_id']): r['source_id'] for r in csv.DictReader(f)}
            with (folder/'players.csv').open(encoding='utf-8', newline='') as f:
                players = {r['id']: r['source_id'] for r in csv.DictReader(f)}
            ranking_history.load(folder, CATALOG)
        self.assertEqual(cites, {('2026-10-01', 'httf-101'): DATED, ('2026-10-01', 'httf-102'): DATED,
                                 ('2026-10-30', 'httf-101'): LATEST, ('2026-10-30', 'httf-102'): LATEST})
        self.assertEqual(players, {'httf-102': DATED})
        self.assertEqual([(c['date'], c['source_id']) for c in manifest['coverage']['rankings']],
                         [('2026-10-01', DATED), ('2026-10-30', LATEST)])
        # Each cited request is recorded as the response that holds its rows.
        self.assertEqual(manifest['requests'][LATEST], source.records[LATEST])
        self.assertEqual(manifest['requests'][DATED]['request']['form']['select-date'], '2026-10-01')

    def test_a_dated_snapshot_that_differs_from_the_published_rows_stops_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'ranking-history'
            held(folder)
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            with self.assertRaisesRegex(SystemExit, 'no longer matches the published rows'):
                self.run_import(folder, self.pages([(1, '101', 'One', '900.5'), (2, '102', 'Two', '799.0')]))
            self.assertEqual({p.name: p.read_bytes() for p in folder.iterdir()}, before)

    def test_a_category_not_asked_for_keeps_its_latest_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'ranking-history'
            held(folder)
            women, _ = key('/customer_ranking.php', {**ranking_form('0'), 'agecategoryid': '10'})
            pages = {SELECTOR_KEY: SELECTOR.replace('</option></select>', '</option><option value="10">Women</option></select>', 1)
                     .format(latest='2026-10-30', older='<option value="2026-10-01">2026-10-01</option>'),
                     women: table([(1, '101', 'One', '700.0')])}
            source = FakeSource(pages)  # holds no Men pages: asking for them would fail
            argv = ['import_rankings.py', '--imports', tmp, '--history', str(folder), '--cache', tmp+'/cache',
                    '--category', '10', '--since', '2026-10-30']
            with patch.object(sys, 'argv', argv), patch.object(import_rankings, 'build', lambda *a: CATALOG), \
                    patch.object(import_rankings, 'Client', lambda *a: source), patch('builtins.print'):
                import_rankings.main()
            manifest = json.loads((folder/'provenance.json').read_text())
        self.assertEqual(manifest['requests'][LATEST]['sha256'], 'old')
        self.assertEqual([(c['category'], c['date'], c['source_id']) for c in manifest['coverage']['rankings']],
                         [('Men', '2026-10-01', LATEST), ('Women', '2026-10-30', women)])

    def replace(self, folder, latest_rows, *extra):
        pages = {SELECTOR_KEY: SELECTOR.format(latest='2026-10-01', older=''), LATEST: table(latest_rows)}
        source = FakeSource(pages)
        argv = ['import_rankings.py', '--imports', str(folder.parent), '--history', str(folder), '--cache', str(folder.parent/'cache'),
                '--category', '15', '--since', '2026-10-30', '--replace', '15:2026-10-01', *extra]
        with patch.object(sys, 'argv', argv), patch.object(import_rankings, 'build', lambda *a: CATALOG), \
                patch.object(import_rankings, 'Client', lambda *a: source), patch('builtins.print'):
            import_rankings.main()
        return source

    def test_a_corrected_snapshot_replaces_the_held_one_whole(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'ranking-history'
            held(folder)
            corrected = [(1, '101', 'One', '900.5'), (2, '103', 'Three', '850.0'), (3, '102', 'Two', '800.0')]
            source = self.replace(folder, corrected)
            manifest = json.loads((folder/'provenance.json').read_text())
            with (folder/'rankings-2026.csv').open(encoding='utf-8', newline='') as f:
                rows = {r['player_id']: (r['rank'], r['source_id']) for r in csv.DictReader(f)}
            with (folder/'players.csv').open(encoding='utf-8', newline='') as f:
                players = sorted(r['id'] for r in csv.DictReader(f))
            ranking_history.load(folder, CATALOG)
        self.assertEqual(rows, {'httf-101': ('1', LATEST), 'httf-103': ('2', LATEST), 'httf-102': ('3', LATEST)})
        self.assertEqual(players, ['httf-102', 'httf-103'])
        self.assertEqual(manifest['coverage']['rankings'], [{'category': 'Men', 'date': '2026-10-01', 'rows': 3, 'source_id': LATEST}])
        self.assertEqual(manifest['requests'][LATEST], source.records[LATEST])

    def test_a_replacement_that_drops_a_ranking_only_player_or_is_rejected_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'ranking-history'
            held(folder)
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            with self.assertRaisesRegex(SystemExit, 'httf-102 citing a response without them'):
                self.replace(folder, [(1, '101', 'One', '900.5')])
            with self.assertRaisesRegex(SystemExit, 'Could not read Men 2026-10-01 again'):  # a malformed row rejects it whole
                self.replace(folder, [(1, '101', 'One', '900.5'), (2, '102', 'Two', '800.0'), ('x', '105', 'Five', '1.0')])
            self.assertEqual({p.name: p.read_bytes() for p in folder.iterdir()}, before)
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(SystemExit, 'pass --category 10'):
            folder = Path(tmp)/'ranking-history'
            held(folder)
            self.replace(folder, OCTOBER, '--replace', '10:2026-10-01')

    def with_exception(self, tmp, player='httf-102'):
        path = Path(tmp)/'exceptions.json'
        path.write_text(json.dumps({'version': 1, 'clubs': [{'player_id': player, 'source_club': '2010',
                                                             'reviewed': '2026-11-26', 'evidence': 'a year in the club field'}]}))
        return path

    def test_a_reviewed_source_club_error_is_published_without_a_club_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'ranking-history'
            held(folder)
            # The source now shows "2010" for httf-102 in the new list and in its dated 1 October list.
            pages = self.pages([(1, '101', 'One', '900.5'), (2, '102', 'Two', '800.0', '2010')])
            pages[LATEST] = table([(1, '102', 'Two', '950.0', '2010'), (2, '101', 'One', '910.0')])
            source = FakeSource(pages)
            argv = ['import_rankings.py', '--imports', tmp, '--history', str(folder), '--cache', tmp+'/cache', '--category', '15',
                    '--since', '2026-10-01', '--exceptions', str(self.with_exception(tmp))]
            with patch.object(sys, 'argv', argv), patch.object(import_rankings, 'build', lambda *a: CATALOG), \
                    patch.object(import_rankings, 'Client', lambda *a: source), patch('builtins.print'):
                import_rankings.main()
            manifest = json.loads((folder/'provenance.json').read_text())
            with (folder/'rankings-2026.csv').open(encoding='utf-8', newline='') as f:
                clubs = {(r['date'], r['player_id']): (r['club_id'], r['source_id']) for r in csv.DictReader(f)}
            ranking_history.load(folder, CATALOG)
        self.assertEqual(clubs, {('2026-10-01', 'httf-101'): (CLUB, DATED), ('2026-10-01', 'httf-102'): (CLUB, DATED),
                                 ('2026-10-30', 'httf-101'): (CLUB, LATEST), ('2026-10-30', 'httf-102'): ('', LATEST)})
        self.assertEqual(manifest['coverage']['source_exceptions'], [
            {'category': 'Men', 'date': '2026-10-01', 'player_id': 'httf-102', 'row': 'httf-ranking-2026-10-01-15-102',
             'source_club': '2010', 'published_club_id': CLUB,
             'published_club_from': {'retrieved_at': '2026-11-20T10:00:00+00:00', 'sha256': 'old'}},
            {'category': 'Men', 'date': '2026-10-30', 'player_id': 'httf-102', 'row': 'httf-ranking-2026-10-30-15-102',
             'source_club': '2010', 'published_club_id': ''}])

    def test_without_a_reviewed_exception_the_club_error_still_stops_or_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'ranking-history'
            held(folder)
            pages = self.pages([(1, '101', 'One', '900.5'), (2, '102', 'Two', '800.0', '2010')])
            with self.assertRaisesRegex(SystemExit, 'no longer matches the published rows'):
                argv_exceptions = str(self.with_exception(tmp, player='httf-101'))  # an entry for someone else does not apply
                source = FakeSource(pages)
                argv = ['import_rankings.py', '--imports', tmp, '--history', str(folder), '--cache', tmp+'/cache', '--category', '15',
                        '--since', '2026-10-01', '--exceptions', argv_exceptions]
                with patch.object(sys, 'argv', argv), patch.object(import_rankings, 'build', lambda *a: CATALOG), \
                        patch.object(import_rankings, 'Client', lambda *a: source), patch('builtins.print'):
                    import_rankings.main()

    def test_exception_entries_must_be_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'exceptions.json'
            path.write_text(json.dumps({'version': 1, 'clubs': [{'player_id': 'httf-1', 'source_club': '2010', 'reviewed': '2026-11-26'}]}))
            with self.assertRaisesRegex(import_rankings.DataError, 'needs exactly'):
                import_rankings.load_exceptions(path)
            self.assertEqual(import_rankings.load_exceptions(Path(tmp)/'absent.json'), {})

    def test_a_snapshot_still_offered_only_as_latest_stays_put(self):
        manifest = {'requests': {LATEST: {'request': {'form': {'select-date': '0'}}}},
                    'coverage': {'rankings': [{'category': 'Men', 'date': '2026-10-01', 'source_id': LATEST}]}}
        self.assertEqual(import_rankings.superseded_latest(manifest, [('2026-08-01', '2026-08-01'), ('2026-10-01', 'latest')]), [])
        self.assertEqual(len(import_rankings.superseded_latest(manifest, [('2026-10-01', '2026-10-01'), ('2026-10-30', 'latest')])), 1)


if __name__ == '__main__':
    unittest.main()
