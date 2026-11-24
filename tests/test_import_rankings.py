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
    return '<table>'+''.join(f'<tr><td>{rank}</td><td></td><td>{number}</td><td>{name}</td><td>Club</td><td></td><td></td><td>{points}</td></tr>'
                             for rank, number, name, points in rows)+'</table>'


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

    def test_a_snapshot_still_offered_only_as_latest_stays_put(self):
        manifest = {'requests': {LATEST: {'request': {'form': {'select-date': '0'}}}},
                    'coverage': {'rankings': [{'category': 'Men', 'date': '2026-10-01', 'source_id': LATEST}]}}
        self.assertEqual(import_rankings.superseded_latest(manifest, [('2026-08-01', '2026-08-01'), ('2026-10-01', 'latest')]), [])
        self.assertEqual(len(import_rankings.superseded_latest(manifest, [('2026-10-01', '2026-10-01'), ('2026-10-30', 'latest')])), 1)


if __name__ == '__main__':
    unittest.main()
