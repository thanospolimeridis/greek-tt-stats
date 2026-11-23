"""Refresh cycles: competitions checked again must keep what is published (synthetic source only)."""
import copy
import csv
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import refresh  # noqa: E402
from batch_import import batch_coverage, checked_in_plan, merge_event  # noqa: E402
from historical import History  # noqa: E402
from import_csv import TYPES, DataError  # noqa: E402
from release_batch import corrections_line, coverage_section  # noqa: E402
from ttscore import BASE, Client, Importer, digest  # noqa: E402
from validate_batch import audit, audit_cache  # noqa: E402
import test_standings  # noqa: E402

OPEN = {'scope': 'available_results', 'date_status': 'ongoing'}


class RecheckRuleTests(unittest.TestCase):
    def test_a_record_counts_only_when_it_is_the_check_the_plan_asks_for(self):
        partial = {'scope': 'available_results', 'snapshot_date': '2026-11-20'}
        self.assertFalse(checked_in_plan(None, {'event': '1'}, '2026-11-27'))
        self.assertTrue(checked_in_plan({}, {'event': '1'}, '2026-11-27'))  # an archive plan: checked once is checked
        self.assertTrue(checked_in_plan(partial, {'event': '1', **OPEN}, '2026-11-20'))
        self.assertFalse(checked_in_plan(partial, {'event': '1', **OPEN}, '2026-11-27'))  # an open one needs the new cutoff
        self.assertFalse(checked_in_plan(partial, {'event': '1'}, '2026-11-27'))  # finished since: needs a complete check
        self.assertFalse(checked_in_plan({}, {'event': '1', **OPEN}, '2026-11-27'))

    def test_progress_counts_this_plan_and_starts_its_own_order(self):
        archive = History(None)
        archive.coverage['events'] = {'1': {'scope': 'available_results', 'snapshot_date': '2026-11-20'}, '2': {}}
        archive.coverage['batch'] = {'plan_sha256': 'an earlier plan', 'processed_order': ['2', '1']}
        plan = {'kind': 'refresh', 'as_of': '2026-11-27', 'deferred': [],
                'queue': [{'event': '1', 'recheck': True, **OPEN}, {'event': '3'}]}
        before = batch_coverage(archive, plan)
        self.assertEqual((before['attempted'], before['pending_events'], before['processed_order']), (0, ['1', '3'], []))
        archive.coverage['events']['1']['snapshot_date'] = '2026-11-27'
        after = batch_coverage(archive, plan)
        self.assertEqual((after['attempted'], after['pending_events'], after['processed_order']), (1, ['3'], ['1']))
        self.assertEqual((after['kind'], after['rechecked']), ('refresh', 1))
        self.assertNotIn('kind', batch_coverage(History(None), {'as_of': 'x', 'queue': [], 'deferred': []}))


def archive_with(**rows):
    archive = History(type('Records', (), {'records': {}})())
    for kind, items in rows.items():
        for row in items:
            archive.data[kind][row['id']] = row
    return archive


def checkpoint(event, **rows):
    return {'data': {kind: {row['id']: row for row in items} for kind, items in rows.items()}, 'requests': {},
            'coverage': {'events': {event: {}}, 'issues': []}, 'adapter_sha256': 'v1'}


class PublishedResultTests(unittest.TestCase):
    old = {'id': 'g1', 'event_id': 'ttscore-7', 'date': '2026-11-14', 'score1': '3', 'score2': '0'}
    other = {'id': 'g9', 'event_id': 'ttscore-8', 'date': '2026-11-14', 'score1': '3', 'score2': '1'}
    new = {'id': 'g2', 'event_id': 'ttscore-7', 'date': '2026-11-21', 'score1': '1', 'score2': '3'}

    def test_a_recheck_adds_results_and_keeps_published_ones(self):
        archive = archive_with(matches=[dict(self.old), dict(self.other)])
        merge_event(archive, checkpoint('7', matches=[{**self.old, 'round': 'relabelled'}, self.new]), '7')
        self.assertEqual(sorted(archive.data['matches']), ['g1', 'g2', 'g9'])
        self.assertNotIn('round', archive.data['matches']['g1'])  # the published row stays exactly as it was

    def test_a_result_the_source_no_longer_shows_stops_for_review(self):
        archive = archive_with(matches=[dict(self.old), dict(self.other)], fixtures=[{'id': 'f1', 'event_id': 'ttscore-7'}])
        with self.assertRaisesRegex(DataError, r'Event 7: 2 published record\(s\) are no longer in the source: f1, g1; .*accepted_source_changes'):
            merge_event(archive, checkpoint('7', matches=[self.new]), '7')
        self.assertIn('g1', archive.data['matches'])  # nothing was removed
        merge_event(archive, checkpoint('7', matches=[self.new]), '7', accepted={'g1', 'f1'})
        self.assertEqual((sorted(archive.data['matches']), archive.data['fixtures']), (['g2', 'g9'], {}))

    def test_a_result_the_source_changed_stops_for_review(self):
        changed = {**self.old, 'score2': '1'}
        archive = archive_with(matches=[dict(self.old)])
        with self.assertRaisesRegex(DataError, 'Event 7: published matches record g1 differs at the source .*accepted_source_changes'):
            merge_event(archive, checkpoint('7', matches=[changed]), '7')
        self.assertEqual(archive.data['matches']['g1']['score2'], '0')
        merge_event(archive, checkpoint('7', matches=[changed]), '7', accepted={'g1'})
        self.assertEqual(archive.data['matches']['g1']['score2'], '1')


class RefreshAuditTests(unittest.TestCase):
    """What a refresh plan may change, and nothing beyond it."""
    request = {'url': BASE+'/x', 'method': 'GET', 'form': None}

    def sample(self):
        evidence = {'k': {'request': self.request, 'retrieved_at': '2026-11-20T07:00:00+00:00', 'sha256': 'old', 'bytes': 1}}
        baseline = {kind: [] for kind in TYPES}
        baseline['events'] = [{'id': 'ttscore-1', 'name': 'League', 'end_date': '2027-02-28'}]
        baseline['matches'] = [{'id': 'g1', 'event_id': 'ttscore-1', 'date': '2026-11-14', 'score1': '3'}]
        baseline['meta'] = {'provenance': {'requests': evidence}}
        plan = {'kind': 'refresh', 'as_of': '2026-11-27', 'created_at': '2026-11-27T06:00:00+00:00', 'deferred': [],
                'queue': [{'event': '1', 'recheck': True, **OPEN}], 'catalog_changes': {'added': [], 'changed': []},
                'accepted_source_changes': []}
        current = copy.deepcopy(baseline)
        current['matches'].append({'id': 'g2', 'event_id': 'ttscore-1', 'date': '2026-11-21', 'score1': '3'})
        archive = History(None)
        archive.coverage['events'] = {'1': {'singles': 2, 'doubles': 0, 'fixtures': 0, 'issues': 0, 'categories_visited': 0,
                                            'categories_selected': 0, 'categories_discovered': 0, 'status': 'partial',
                                            'snapshot_date': '2026-11-27', **OPEN}}
        current['meta'] = {'provenance': {'coverage': archive.coverage, 'requests': copy.deepcopy(evidence)},
                           'season_coverage': {}, 'dataset_sha256': 'test'}
        return current, baseline, plan, archive

    def audited(self, current, baseline, plan, archive):
        batch_coverage(archive, plan)
        return audit(current, baseline, plan)

    def test_a_recheck_that_only_adds_results_passes(self):
        report = self.audited(*self.sample())
        self.assertEqual((report['checked'], report['pending'], report['source_evidence_superseded']), (1, 0, 0))

    def test_evidence_may_be_replaced_only_by_the_same_request_made_during_the_cycle(self):
        current, baseline, plan, archive = self.sample()
        fresh = current['meta']['provenance']['requests']['k']
        fresh.update(retrieved_at='2026-11-27T07:00:00+00:00', sha256='new')
        self.assertEqual(self.audited(current, baseline, plan, archive)['source_evidence_superseded'], 1)
        fresh['retrieved_at'] = '2026-11-27T05:59:59+00:00'  # before the cycle began
        with self.assertRaisesRegex(DataError, 'Baseline source evidence changed'):
            self.audited(current, baseline, plan, archive)
        fresh.update(retrieved_at='2026-11-27T07:00:00+00:00', request={**self.request, 'url': BASE+'/y'})
        with self.assertRaisesRegex(DataError, 'Baseline source evidence changed'):
            self.audited(current, baseline, plan, archive)
        current, baseline, plan, archive = self.sample()
        current['meta']['provenance']['requests']['k'].update(retrieved_at='2026-11-27T07:00:00+00:00', sha256='new')
        del plan['created_at']  # an archive plan never replaces evidence
        with self.assertRaisesRegex(DataError, 'Baseline source evidence changed'):
            self.audited(current, baseline, plan, archive)

    def test_listing_changes_must_be_the_ones_the_plan_records(self):
        current, baseline, plan, archive = self.sample()
        current['events'][0]['end_date'] = '2027-03-07'
        with self.assertRaisesRegex(DataError, r'Baseline events record changed: ttscore-1\.end_date'):
            self.audited(current, baseline, plan, archive)
        plan['catalog_changes']['changed'] = [{'event': '1', 'field': 'end_date', 'from': '2027-02-28', 'to': '2027-03-07'}]
        self.audited(current, baseline, plan, archive)
        current['events'][0]['name'] = 'Renamed'
        with self.assertRaisesRegex(DataError, r'ttscore-1\.name'):
            self.audited(current, baseline, plan, archive)

    def test_published_results_change_only_when_a_reviewer_accepted_it(self):
        for change in ('removed', 'rescored'):
            with self.subTest(change=change):
                current, baseline, plan, archive = self.sample()
                if change == 'removed':
                    current['matches'].pop(0)
                    archive.coverage['events']['1']['singles'] = 1
                else:
                    current['matches'][0]['score1'] = '2'
                with self.assertRaisesRegex(DataError, 'Baseline matches record (missing|changed): g1'):
                    self.audited(current, baseline, plan, archive)
                plan['accepted_source_changes'] = ['g1']
                self.audited(current, baseline, plan, archive)

    def test_a_competition_not_checked_again_yet_is_pending(self):
        current, baseline, plan, archive = self.sample()
        archive.coverage['events']['1']['snapshot_date'] = '2026-11-20'
        batch_coverage(archive, plan)
        with self.assertRaisesRegex(DataError, 'New matches appear for an unchecked competition'):
            audit(current, baseline, plan, allow_pending=True)
        current['matches'].pop()
        self.assertEqual(audit(current, baseline, plan, allow_pending=True)['pending'], 1)
        with self.assertRaisesRegex(DataError, '1 eligible competitions remain unchecked'):
            audit(current, baseline, plan)


def store(cache, path, body, form=None, when='2026-11-20T07:00:00+00:00'):
    """Write one response the way the collector's client caches it. Returns the request key."""
    request = {'url': BASE+path, 'method': 'POST' if form is not None else 'GET', 'form': form}
    key, data = digest(json.dumps(request, sort_keys=True).encode()), body.encode()
    cache.mkdir(parents=True, exist_ok=True)
    (cache/f'{key}.body').write_bytes(data)
    (cache/f'{key}.json').write_text(json.dumps({'request': request, 'retrieved_at': when, 'sha256': digest(data),
                                                 'bytes': len(data), 'status': 200}, ensure_ascii=False, indent=2)+'\n')
    return key


class CacheGenerationTests(unittest.TestCase):
    def test_published_evidence_is_found_in_whichever_cycle_retrieved_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp)/'first', Path(tmp)/'second'
            key = store(first, '/x', 'as it was')
            self.assertEqual(store(second, '/x', 'as it is now', when='2026-11-27T07:00:00+00:00'), key)
            record = lambda cache: {key: json.loads((cache/f'{key}.json').read_text())}  # noqa: E731
            self.assertEqual(audit_cache(record(first), [second, first]), 1)
            self.assertEqual(audit_cache(record(second), [second, first]), 1)
            self.assertEqual(audit_cache(record(first), first), 1)  # one folder, as before
            with self.assertRaisesRegex(DataError, 'Source cache differs from published evidence'):
                audit_cache(record(second), [first])
            (second/f'{key}.body').write_text('tampered')
            with self.assertRaisesRegex(DataError, 'Source cache differs from published evidence'):
                audit_cache(record(second), [second, first])


class RefreshPlanTests(unittest.TestCase):
    def plan(self, events, records, as_of='2026-11-27', leagues=()):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with (base/'events.csv').open('w', newline='') as target:
                writer = csv.writer(target)
                writer.writerow(['id', 'season', 'start_date', 'end_date'])
                writer.writerows(events)
            coverage = {'events': records, 'leagues': {ident: {} for ident in leagues}}
            (base/'provenance.json').write_text(json.dumps({'coverage': coverage}))
            return refresh.refresh_plan(base, as_of, '2026-11-27T06:00:00+00:00', {'added': [], 'changed': []}, {'as_of': 'earlier'})

    def test_only_open_and_new_competitions_are_queued(self):
        partial = {'scope': 'available_results', 'snapshot_date': '2026-11-20'}
        plan = self.plan([
            ('ttscore-1', '2025-26', '2025-09-01', '2026-03-01'),   # checked as finished: never again
            ('ttscore-2', '2026-27', '2026-09-01', '2027-02-28'),   # open when checked, still open
            ('ttscore-3', '2026-27', '2026-10-01', '2026-11-22'),   # open when checked, finished since
            ('ttscore-4', '2020-21', '', ''),                       # undated listing from an old season
            ('ttscore-5', '2026-27', '', ''),                       # undated listing of the current season
            ('ttscore-6', '2026-27', '2026-11-21', '2026-11-22'),   # new and finished
            ('ttscore-7', '2026-27', '2026-11-27', '2026-11-29'),   # new and under way
            ('ttscore-8', '2026-27', '2026-12-12', '2026-12-13'),   # not started
            ('ttscore-9', '2025-26', '2025-09-01', '2026-03-01'),   # the first league, imported before batches
            ('ttscore-10', '2026-27', '2026-11-20', '2026-11-27')], # ends on the cutoff day: still open
            {'1': {}, '2': partial, '3': partial, '4': partial, '5': partial, '10': partial}, leagues=['9', '2'])
        queued = {item['event']: item for item in plan['queue']}
        self.assertEqual(sorted(queued, key=int), ['2', '3', '5', '6', '7', '10'])
        self.assertEqual({k: v.get('scope', 'finished') for k, v in queued.items()},
                         {'2': 'available_results', '3': 'finished', '5': 'available_results', '6': 'finished',
                          '7': 'available_results', '10': 'available_results'})
        self.assertEqual({k for k, v in queued.items() if v.get('recheck')}, {'2', '3', '5', '10'})
        self.assertEqual(queued['5']['date_status'], 'undated')
        self.assertEqual(plan['deferred'], [{'event': '8', 'season': '2026-27', 'end_date': '2026-12-13', 'reason': 'not_started_by_cutoff'}])
        self.assertEqual((plan['kind'], plan['schema_version'], plan['accepted_source_changes']), ('refresh', 3, []))
        self.assertTrue(plan['previous_plan_sha256'])
        # Every queued item is unchecked under its own plan, so the collector will process it.
        records = {'1': {}, '2': partial, '3': partial, '5': partial, '10': partial}
        self.assertFalse(any(checked_in_plan(records.get(i['event']), i, plan['as_of']) for i in plan['queue']))


def grid(*events):
    cards = ''.join(f'<a href="{BASE}/customer/24/event/{ident}"><h4>{name}</h4><h6>{dates}</h6><h6>Hall</h6></a>'
                    for ident, name, dates in events)
    return f'<div class="grid">{cards}</div>'


def sheet(game, row, home_wins):
    entry = {'ID': row, 'Home': '11', 'Away': '12', 'Home_2': '-1', 'Away_2': '-1', 'Countable': '1', 'Winsets': '3',
             'Score': '3-0' if home_wins else '0-3', 'Winner': '11' if home_wins else '12'}
    for i in range(1, 8):
        entry.update({f'{i}H': ('11' if home_wins else '5') if i <= 3 else '0', f'{i}A': ('5' if home_wins else '11') if i <= 3 else '0'})
    return json.dumps({'data': [{'team_games': entry, 'homep_1': {'AM': '111', 'FirstName': 'A', 'LastName': 'Test'},
                                 'awayp_1': {'AM': '112', 'FirstName': 'B', 'LastName': 'Test'}}]})


class Source:
    """A synthetic TTScore: two leagues, written into a cache folder as it looked at one moment."""
    LISTING = {'9': ('2026-27', [('1', 'Open League', '01/09/26-28/02/27')]),
               '8': ('2025-26', [('2', 'Past League', '01/09/25-28/02/26')])}

    def __init__(self, cache, when, listing=None):
        self.cache, self.when, self.listing = cache, when, listing or self.LISTING
        self.put('/robots.txt', 'User-agent: *\nAllow: /\n')
        self.put('/customer/24', '<a href="customer_events.php?customer=24">Events</a>')
        seasons = ''.join(f'<option value="{value}">{label}</option>' for value, (label, _) in self.listing.items())
        self.put('/customer_events.php?customer=24', f'<select name="select-season"><option value="">All</option>{seasons}</select>')
        self.put('/customer_events.php', grid(*(e for _, events in self.listing.values() for e in events)),
                 {'customer': '24', 'season': '', 'getStats': '1'})
        for value, (_, events) in self.listing.items():
            self.put('/customer_events.php', grid(*events), {'customer': '24', 'season': value, 'getStats': '1'})

    def put(self, path, body, form=None):
        return store(self.cache, path, body, form, self.when)

    def league(self, event, group, fixtures, table, sheets):
        """fixtures: [(game, 'yy-mm-dd', score)]; sheets: {game: (row id, home wins)} to write this time."""
        link = f'{BASE}/tournament_groups_league.php?event={event}&customer=24'
        self.put(f'/customer/24/event/{event}', f"<a onclick=\"loadQueryResults('{link}')\">League</a>")
        self.put(f'/tournament_groups_league.php?event={event}&customer=24',
                 '<select name="agecategoryid_league"><option value="5">Men</option></select>')
        self.put('/tournament_groups_league.php', test_standings.table(group, table),
                 {'event': event, 'customer': '24', 'getStats': '1', 'agecategoryid_league': '5'})
        rows = ''.join(f'<tr id="game-{game}"><td>1</td><td>{day} / 12:00</td><td>1</td><td>Club A - Club B</td><td></td><td>{score}</td></tr>'
                       for game, day, score in fixtures)
        self.put(f'/tournament_groups_league.php?group={group}&customer=24', f'<table class="scheduleTable">{rows}</table>')
        if fixtures:
            first = fixtures[0][0]
            self.put(f'/game-team.php?game={first}&customer=24', f'<a href="/admin/ajax/team_games.php?game={first}">sheet</a>')
        for game, (row, home_wins) in sheets.items():
            self.put(f'/admin/ajax/team_games.php?game={game}&customer=24', sheet(game, row, home_wins))


def rows(folder, kind):
    with (folder/f'{kind}.csv').open(encoding='utf-8', newline='') as source:
        return {row['id']: row for row in csv.DictReader(source)}


class RefreshCycleTests(unittest.TestCase):
    """Three cycles end to end, offline, with the real collector, audit, replay and promotion."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.published, self.standings = self.root/'published', self.root/'standings'
        (self.root/'README.md').write_text('# Test\n\n## Current coverage\n\nold\n\n## Use and build\n\nrest\n')

    def tearDown(self):
        self.tmp.cleanup()

    def cycle(self, as_of):
        return refresh.Cycle(as_of, destination=self.published, readme=self.root/'README.md', plan_path=self.root/'plan.json',
                             cycles=self.root/'cycles', first_cache=self.root/'no-first-cache', pause=self.root/'pause',
                             clock=lambda: f'{as_of}T06:00:00+00:00')

    def run_cycle(self, cycle):
        plan = refresh.prepare(cycle, offline=True)
        seeded = refresh.collect(cycle, plan, offline=True)
        summary = refresh.release(cycle)
        refresh.refresh_standings(cycle, plan, folder=self.standings)
        return plan, seeded, summary

    def first_cycle(self):
        """20 November: the open league has played one of its two fixtures; the past league is complete."""
        cycle = self.cycle('2026-11-20')
        source = Source(cycle.cache, '2026-11-20T07:00:00+00:00')
        source.league('1', '77', [('101', '26-11-14', '1-0'), ('102', '26-11-21', '0-0')],
                      [(1, 'Club A - Club A', 1, 0, 0, 3), (2, 'Club B - Club B', 0, 1, 0, 1)], {'101': ('1001', True)})
        source.league('2', '88', [('201', '26-01-10', '1-0')],
                      [(1, 'Club A - Club A', 1, 0, 0, 3), (2, 'Club B - Club B', 0, 1, 0, 1)], {'201': ('2001', True)})
        listing = Importer(Client(cycle.cache, offline=True))
        listing.catalog()
        with open(self.root/'export.log', 'w') as log, __import__('contextlib').redirect_stdout(log):
            listing.export(self.published)
        return cycle, self.run_cycle(cycle)

    def second_cycle(self, fixtures=(('101', '26-11-14', '1-0'), ('102', '26-11-21', '0-1')), as_of='2026-11-27'):
        """A week later the second fixture is played. Only its sheet is new at the source."""
        cycle = self.cycle(as_of)
        source = Source(cycle.cache, f'{as_of}T07:00:00+00:00')
        source.league('1', '77', list(fixtures), [(1, 'Club A - Club A', 1, 1, 0, 4), (2, 'Club B - Club B', 1, 1, 0, 4)],
                      {'102': ('1002', False)})
        return cycle

    def test_the_first_check_takes_an_open_league_as_far_as_its_cutoff(self):
        cycle, (plan, seeded, summary) = self.first_cycle()
        self.assertEqual([(i['event'], i.get('scope', 'finished'), i.get('recheck', False)) for i in plan['queue']],
                         [('2', 'finished', False), ('1', 'available_results', False)])
        self.assertEqual(seeded, 0)
        self.assertEqual(sorted(rows(self.published, 'fixtures')), ['ttscore-game-101', 'ttscore-game-201'])
        self.assertEqual(sorted(rows(self.published, 'matches')), ['ttscore-team-game-1001', 'ttscore-team-game-2001'])
        self.assertEqual((summary['checked'], summary['pending']), (2, 0))
        self.assertEqual(len(rows(self.standings, 'standings')), 4)

    def test_a_refresh_adds_the_new_fixture_and_keeps_everything_published(self):
        first, _ = self.first_cycle()
        before = {kind: rows(self.published, kind) for kind in ('matches', 'fixtures', 'players', 'clubs')}
        past_table = {k: v for k, v in rows(self.standings, 'standings').items() if v['event_id'] == 'ttscore-2'}
        cycle = self.second_cycle()
        plan, seeded, summary = self.run_cycle(cycle)
        self.assertEqual([(i['event'], i['scope'], i['recheck']) for i in plan['queue']], [('1', 'available_results', True)])
        self.assertEqual(seeded, 1)  # the sheet behind the published fixture was not requested again
        key = refresh.sheet_key('101')
        self.assertEqual((cycle.cache/f'{key}.json').read_text(), (first.cache/f'{key}.json').read_text())
        after = {kind: rows(self.published, kind) for kind in before}
        for kind, published in before.items():
            for ident, row in published.items():
                self.assertEqual(after[kind][ident], row, f'{kind} {ident}')
        self.assertEqual(sorted(set(after['fixtures'])-set(before['fixtures'])), ['ttscore-game-102'])
        self.assertEqual(after['matches']['ttscore-team-game-1002']['winner_id'], 'httf-112')
        report = json.loads(next(cycle.releases.glob('*/audit.json')).read_text())
        self.assertEqual((report['checked'], report['offline_replayed_competitions']), (1, 1))
        self.assertGreater(report['source_evidence_superseded'], 0)  # the listing and the league pages were read again
        self.assertEqual(report['previous_release_preserved']['matches'], 2)
        manifest = json.loads((self.published/'provenance.json').read_text())
        record = manifest['coverage']['events']['1']
        self.assertEqual((record['snapshot_date'], record['singles'], record['fixtures']), ('2026-11-27', 2, 2))
        self.assertEqual(manifest['requests'][key]['retrieved_at'], '2026-11-20T07:00:00+00:00')  # carried forward as retrieved
        self.assertEqual((manifest['coverage']['batch']['kind'], manifest['coverage']['batch']['rechecked']), ('refresh', 1))
        readme = (self.root/'README.md').read_text()
        self.assertIn('The latest refresh checked **1 of 1 competitions**', readme)
        self.assertIn('## Use and build\n\nrest\n', readme)
        table = rows(self.standings, 'standings')
        self.assertEqual({k: v for k, v in table.items() if v['event_id'] == 'ttscore-2'}, past_table)  # other leagues untouched
        self.assertEqual({(v['points'], v['as_of']) for v in table.values() if v['event_id'] == 'ttscore-1'}, {('4', '2026-11-27')})
        # Running the finished steps again changes nothing.
        again = self.run_cycle(cycle)
        self.assertEqual((again[1], again[2]['counts']), (0, summary['counts']))
        self.assertEqual({kind: rows(self.published, kind) for kind in before}, after)

    def test_a_refresh_stops_when_a_published_fixture_has_left_the_source(self):
        self.first_cycle()
        self.run_cycle(self.second_cycle())
        published = {kind: (self.published/f'{kind}.csv').read_bytes() for kind in ('matches', 'fixtures')}
        cycle = self.second_cycle(fixtures=(('102', '26-11-21', '0-1'),), as_of='2026-12-04')
        plan = refresh.prepare(cycle, offline=True)
        with self.assertRaisesRegex(DataError, r'Event 1: 2 published record\(s\) are no longer in the source: '
                                               'ttscore-game-101, ttscore-team-game-1001; .*accepted_source_changes'):
            refresh.collect(cycle, plan, offline=True)
        self.assertEqual({kind: (self.published/f'{kind}.csv').read_bytes() for kind in published}, published)
        plan['accepted_source_changes'] = ['ttscore-game-101', 'ttscore-team-game-1001']
        (self.root/'plan.json').write_text(json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2)+'\n')
        plan, _, summary = self.run_cycle(cycle)
        self.assertEqual(plan['accepted_source_changes'], ['ttscore-game-101', 'ttscore-team-game-1001'])
        self.assertEqual(sorted(rows(self.published, 'fixtures')), ['ttscore-game-102', 'ttscore-game-201'])
        self.assertEqual(sorted(rows(self.published, 'matches')), ['ttscore-team-game-1002', 'ttscore-team-game-2001'])

    def test_listing_changes_are_recorded_and_a_delisted_competition_stops_the_refresh(self):
        self.first_cycle()
        cycle = self.cycle('2026-11-27')
        listing = {'9': ('2026-27', [('1', 'Open League', '01/09/26-07/03/27'), ('3', 'New Cup', '12/12/26-13/12/26')]),
                   '8': ('2025-26', [('2', 'Past League', '01/09/25-28/02/26')])}
        source = Source(cycle.cache, '2026-11-27T07:00:00+00:00', listing)
        source.league('1', '77', [('101', '26-11-14', '1-0')], [(1, 'Club A - Club A', 1, 0, 0, 3), (2, 'Club B - Club B', 0, 1, 0, 1)], {})
        plan, _, _ = self.run_cycle(cycle)
        self.assertEqual(plan['catalog_changes'], {'added': ['3'], 'changed': [{'event': '1', 'field': 'end_date', 'from': '2027-02-28', 'to': '2027-03-07'}]})
        self.assertEqual([d['event'] for d in plan['deferred']], ['3'])
        events = rows(self.published, 'events')
        self.assertEqual((events['ttscore-1']['end_date'], events['ttscore-3']['name']), ('2027-03-07', 'New Cup'))
        gone = self.cycle('2026-12-04')
        Source(gone.cache, '2026-12-04T07:00:00+00:00', {'9': ('2026-27', [('1', 'Open League', '01/09/26-07/03/27')]),
                                                         '8': ('2025-26', [('2', 'Past League', '01/09/25-28/02/26')])})
        with self.assertRaisesRegex(DataError, r'1 archived competition\(s\) are no longer in the public listing, first ttscore-3'):
            refresh.prepare(gone, offline=True)
        self.assertFalse((gone.base).exists())

    def test_a_cycle_cannot_reach_back_before_the_last_check(self):
        self.first_cycle()
        with self.assertRaisesRegex(DataError, 'already checked through 2026-11-20'):
            refresh.prepare(self.cycle('2026-11-19'))

    def test_a_finished_cycle_keeps_its_evidence_and_drops_working_copies(self):
        cycle, _ = self.first_cycle()
        refresh.tidy(cycle)
        self.assertEqual(sorted(p.name for p in cycle.folder.iterdir() if p.name != 'refresh.log'),
                         ['audit.json', 'cache', 'cycle.json', 'plan.json', 'state.json'])
        self.assertEqual(json.loads((cycle.folder/'plan.json').read_text())['as_of'], '2026-11-20')


class StagingTests(unittest.TestCase):
    """The refreshed inputs go to develop as one commit; nothing else may ride along."""
    clean = {('remote', 'get-url', 'origin'): refresh.REMOTE, ('rev-parse', 'HEAD'): 'aaa', ('rev-parse', 'origin/develop'): 'aaa'}

    def git(self, answers, calls=None):
        def fake(*args):
            if calls is not None:
                calls.append(args)
            return answers.get(args, '')
        return patch.object(refresh, 'git', fake)

    def test_only_the_refreshed_inputs_may_change(self):
        self.assertEqual(refresh.unexpected(['README.md', 'data/import-plan.json', 'imports/matches.csv', 'imports/provenance.json',
                                             'imports/standings/standings.csv', 'imports/ranking-history/rankings-2026.csv']), [])
        self.assertEqual(refresh.unexpected(['imports/matches.csv', 'src/app.js', 'scripts/refresh.py', 'VERSION', 'imports/notes.txt']),
                         ['VERSION', 'imports/notes.txt', 'scripts/refresh.py', 'src/app.js'])

    def test_changed_paths_reads_real_git_status(self):
        """The first porcelain line of an unstaged change starts with a space that must survive."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            quiet = ['-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid']
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            for name in ('README.md', 'data/import-plan.json'):
                (root/name).parent.mkdir(parents=True, exist_ok=True)
                (root/name).write_text('before\n')
            subprocess.run(['git', *quiet, 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', *quiet, 'commit', '-q', '-m', 'start'], cwd=root, check=True)
            for name in ('README.md', 'data/import-plan.json'):
                (root/name).write_text('after\n')
            (root/'notes.txt').write_text('new\n')
            with patch.object(refresh, 'ROOT', root):
                self.assertEqual(sorted(refresh.changed_paths()), ['README.md', 'data/import-plan.json', 'notes.txt'])

    def test_a_refresh_starts_at_the_staging_branch_with_a_clean_tree(self):
        with self.git(self.clean):
            refresh.check_checkout(resuming=False)
        with self.git({**self.clean, ('rev-parse', 'origin/develop'): 'bbb'}), self.assertRaisesRegex(DataError, 'checkout at origin/develop'):
            refresh.check_checkout(resuming=False)
        porcelain = ('status', '--porcelain', '--untracked-files=all')
        with self.git({**self.clean, porcelain: ' M imports/matches.csv'}), self.assertRaisesRegex(DataError, 'other changes, first imports/matches.csv'):
            refresh.check_checkout(resuming=False)
        with self.git({**self.clean, porcelain: ' M imports/matches.csv\n M README.md'}):
            refresh.check_checkout(resuming=True)  # a resumed cycle has already promoted its inputs
        with self.git({**self.clean, porcelain: ' M imports/matches.csv\n?? notes.txt'}), self.assertRaisesRegex(DataError, 'first notes.txt'):
            refresh.check_checkout(resuming=True)
        with self.git({**self.clean, ('remote', 'get-url', 'origin'): 'https://example.invalid/x.git'}), self.assertRaisesRegex(DataError, 'Remote changed'):
            refresh.check_checkout(resuming=False)

    def test_the_commit_is_pushed_to_develop_and_validated(self):
        porcelain = ('status', '--porcelain', '--untracked-files=all')
        summary = {'counts': {'matches': 90000}, 'checked': 21}
        cycle = refresh.Cycle('2026-11-27')
        calls = []
        listing = type('Done', (), {'returncode': 0, 'stdout': json.dumps([{'name': 'Validate archive', 'status': 'completed', 'conclusion': 'success'},
                                                                           {'name': 'Something else', 'status': 'completed', 'conclusion': 'failure'}])})()
        with self.git({porcelain: ' M imports/matches.csv\n M README.md', ('rev-parse', 'HEAD'): 'abc1234'}, calls), \
                patch.object(refresh.subprocess, 'run', lambda *a, **k: listing), patch.object(refresh, 'say', lambda text: None):
            self.assertEqual(refresh.stage(cycle, summary), 'abc1234')
        self.assertEqual(calls[1:], [('add', '--', 'imports/matches.csv', 'README.md'),
                                     ('commit', '-m', 'Refresh results through 2026-11-27: 90000 singles, 21 competitions checked'),
                                     ('rev-parse', 'HEAD'), ('push', 'origin', 'HEAD:develop')])
        failed = type('Done', (), {'returncode': 0, 'stdout': json.dumps([{'name': 'Validate archive', 'status': 'completed', 'conclusion': 'failure'}])})()
        with self.git({porcelain: ' M README.md', ('rev-parse', 'HEAD'): 'abc1234'}), patch.object(refresh.subprocess, 'run', lambda *a, **k: failed), \
                patch.object(refresh, 'say', lambda text: None), self.assertRaisesRegex(DataError, '"Validate archive" failed for abc1234'):
            refresh.stage(cycle, summary)
        calls.clear()
        with self.git({porcelain: ' M src/app.js'}, calls), self.assertRaisesRegex(DataError, 'Unexpected paths changed, first src/app.js'):
            refresh.stage(cycle, summary)
        self.assertEqual(calls, [porcelain])  # nothing was added, committed or pushed
        with self.git({}), patch.object(refresh, 'say', lambda text: None):
            self.assertIsNone(refresh.stage(cycle, summary))

    def test_the_refresh_is_outside_the_adapter_fingerprint(self):
        source = (Path(refresh.__file__).parent/'batch_import.py').read_text()
        self.assertNotIn('refresh.py', source.split('def adapter_hash')[1].split('def ')[0])


class CoverageWordingTests(unittest.TestCase):
    def test_identity_corrections_are_counted_from_the_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'identity-corrections.json'
            self.assertEqual(corrections_line(path), '')
            path.write_text(json.dumps({'players': [{}, {}], 'clubs': [{}]}))
            self.assertIn('**3 reviewed identity corrections**', corrections_line(path))
            self.assertIn('2 athletes', corrections_line(path))
            path.write_text(json.dumps({'players': [], 'clubs': []}))
            self.assertEqual(corrections_line(path), '')

    def test_a_refresh_is_described_as_one(self):
        batch = {'attempted': 19, 'eligible': 21, 'pending': 2, 'deferred': [{}], 'as_of': '2026-11-27'}
        data = {kind: [] for kind in TYPES}
        data['meta'] = {'legacy_events_not_in_current_catalog': [],
                        'provenance': {'coverage': {'batch': batch, 'event_catalog': {'count': 520}, 'issues': [], 'rankings': []}}}
        archive = coverage_section(data, dt.date(2026, 11, 28))
        self.assertIn('The current resumable batch has checked **19 of 21 additional eligible competitions**', archive)
        batch.update(kind='refresh', rechecked=17)
        text = coverage_section(data, dt.date(2026, 11, 28))
        self.assertIn('The latest refresh checked **19 of 21 competitions** that were still in progress or newly listed, '
                      '17 of them already in the archive. **2 remain queued**, and 1 listings remain explicitly deferred', text)
        self.assertIn('dated on or before 27 November 2026', text)
        self.assertNotIn('resumable batch', text)


if __name__ == '__main__':
    unittest.main()
