#!/usr/bin/env python3
"""Refresh the archive: check again the competitions that were still open and add new ones.

The archive collector checks each competition once. A refresh is one more cycle on
top of it. The public listing is read again; competitions that were in progress at
their last check, and newly listed ones that have started, are queued in a new frozen
plan; and their pages are fetched into the cycle's own cache folder, so earlier source
evidence is never overwritten. The usual release audit and offline replay then run,
with the plan naming the only things a refresh may change. Official rankings and
league standings are refreshed in the same pass, and the result is staged on
`develop`. Publishing stays a separate, deliberate release (README, "Releases and
versions").

    python3 scripts/refresh.py                 what a refresh would queue; makes no requests
    python3 scripts/refresh.py run             one cycle through yesterday, staged on develop
    python3 scripts/refresh.py run --as-of 2026-11-29 --no-stage
    python3 scripts/refresh.py rehearse        a whole cycle offline in a scratch folder; changes nothing

A cycle lives in capture/refresh/<cutoff>/. Stopping is safe at any point: run the
same command again and it resumes. This file is outside batch_import.adapter_hash().
"""
import argparse
import contextlib
import csv
import datetime as dt
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from batch_import import atomic_json, batch_coverage, catalog_fingerprint, plan_digest  # noqa: E402
from historical import History, restore_base  # noqa: E402
from import_csv import ROOT, TYPES, DataError  # noqa: E402
from ttscore import BASE, Client, Importer, digest  # noqa: E402

CAPTURE = ROOT/'capture'
CYCLES = CAPTURE/'refresh'
FIRST_CACHE = CAPTURE/'ttscore'
REMOTE = 'https://github.com/thanospolimeridis/greek-tt-stats.git'
STAGING_BRANCH = 'develop'
VALIDATION = 'Validate archive'
BUNDLE = tuple(f'{kind}.csv' for kind in TYPES)+('provenance.json',)
LISTING_FIELDS = ('name', 'season', 'start_date', 'end_date', 'region', 'source_url', 'source_id', 'source_status')
# What a refresh may change in the repository; anything else stops the staging step.
STAGED_PATHS = ('README.md', 'data/import-plan.json', 'imports/provenance.json', *(f'imports/{kind}.csv' for kind in TYPES))
STAGED_FOLDERS = ('imports/ranking-history/', 'imports/standings/')


def number(ident):
    return int(ident.removeprefix('ttscore-'))


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def yesterday():
    """Default cutoff: results entered during a match day can still be incomplete."""
    return (dt.datetime.now(ZoneInfo('Europe/Athens')).date()-dt.timedelta(days=1)).isoformat()


def say(text):
    print(text, flush=True)


def copy_bundle(source, target):
    target.mkdir(parents=True, exist_ok=True)
    for name in BUNDLE:
        shutil.copyfile(source/name, target/name)


def same_bundle(first, second):
    return all((first/name).read_bytes() == (second/name).read_bytes() for name in BUNDLE)


def apply_catalog(baseline, target, client):
    """Write the baseline with the public listing as it is now; return what the listing changed.

    New competitions are added and changed listing fields are taken over, each recorded
    for the plan. A competition that is no longer listed stops the refresh: its row cites
    a listing that would no longer show it, which needs a person to decide.
    """
    base = History(client)
    restore_base(base, baseline)
    listing = Importer(client)
    listing.catalog()
    known, listed = base.data['events'], listing.data['events']
    missing = sorted(set(known)-set(listed), key=number)
    if missing:
        raise DataError(f'{len(missing)} archived competition(s) are no longer in the public listing, first {missing[0]}; '
                        'review before refreshing')
    changes = {'added': [], 'changed': []}
    for ident in sorted(listed, key=number):
        row = {field: value for field, value in listed[ident].items() if value != ''}
        if ident not in known:
            known[ident] = row
            changes['added'].append(str(number(ident)))
            continue
        for field in LISTING_FIELDS:
            old, new = known[ident].get(field, ''), row.get(field, '')
            if old != new:
                changes['changed'].append({'event': str(number(ident)), 'field': field, 'from': old, 'to': new})
                if new:
                    known[ident][field] = new
                else:
                    del known[ident][field]
    base.coverage['event_catalog'] = listing.coverage['event_catalog']
    with contextlib.redirect_stdout(io.StringIO()):
        base.export(target)
    return changes


def refresh_plan(base, as_of, created_at, changes, previous=None):
    """Queue what a refresh has to look at, from the listing and the archive's own coverage.

    - never checked and finished: a normal, complete check;
    - never checked, started and still running (or undated): the results available so far;
    - checked while open: checked again, complete if it has finished since. An undated
      listing from an earlier season is left alone, as nothing new is expected there;
    - not started by the cutoff: deferred, with the reason.
    A competition already checked as finished is never queued again.
    """
    with (base/'events.csv').open(encoding='utf-8', newline='') as source:
        rows = list(csv.DictReader(source))
    coverage = json.loads((base/'provenance.json').read_text(encoding='utf-8'))['coverage']
    records = coverage.get('events', {})
    legacy = set(coverage.get('leagues', {}))-set(records)  # the first league, imported before batches existed
    current = max(row['season'] for row in rows)
    queue, deferred = [], []
    for row in sorted(rows, key=lambda r: (r.get('end_date') or '9999', number(r['id']))):
        ident = str(number(row['id']))
        end, start = row.get('end_date') or '', row.get('start_date') or ''
        item = {'event': ident, 'season': row['season'], 'end_date': end}
        finished = bool(end) and end < as_of
        partial = {**item, 'scope': 'available_results', 'date_status': 'ongoing' if end else 'undated'}
        record = records.get(ident)
        if record is None:
            if ident in legacy:
                continue
            if finished:
                queue.append(item)
            elif not start or start <= as_of:
                queue.append(partial)
            else:
                deferred.append({**item, 'reason': 'not_started_by_cutoff'})
        elif record.get('scope') == 'available_results':
            if finished:
                queue.append({**item, 'recheck': True})
            elif end or row['season'] == current:
                queue.append({**partial, 'recheck': True})
    return {'schema_version': 3, 'kind': 'refresh', 'as_of': as_of, 'created_at': created_at,
            'catalog_sha256': catalog_fingerprint(base/'events.csv'),
            'previous_plan_sha256': plan_digest(previous) if previous else None,
            'catalog_changes': changes, 'accepted_source_changes': [],
            'queue': queue, 'deferred': deferred, 'include_available_results': True, 'historical_complete': False}


def sheet_key(game):
    request = {'url': f'{BASE}/admin/ajax/team_games.php?game={game}&customer=24', 'method': 'GET', 'form': None}
    return digest(json.dumps(request, sort_keys=True).encode())


def seed_sheets(plan, base, cache, older):
    """Carry forward the match sheets of fixtures the archive already publishes.

    A competition checked again asks for every fixture's sheet. The sheets behind
    published fixtures are copied into this cycle's cache with their original
    retrieval record, so only the listing pages and new fixtures cost a request. A
    correction the source makes later to an old sheet is not seen this way;
    --recheck-sheets fetches them all again.
    """
    rechecked = {'ttscore-'+item['event'] for item in plan['queue'] if item.get('recheck')}
    published = json.loads((base/'provenance.json').read_text(encoding='utf-8'))['requests']
    cache.mkdir(parents=True, exist_ok=True)
    copied = 0
    with (base/'fixtures.csv').open(encoding='utf-8', newline='') as source:
        for row in csv.DictReader(source):
            if row['event_id'] not in rechecked:
                continue
            key = sheet_key(row['id'].removeprefix('ttscore-game-'))
            if key not in published or (cache/f'{key}.json').exists():
                continue
            for folder in older:
                record = folder/f'{key}.json'
                if record.exists() and json.loads(record.read_text()) == published[key]:
                    shutil.copyfile(folder/f'{key}.body', cache/f'{key}.body')
                    shutil.copyfile(record, cache/f'{key}.json')
                    copied += 1
                    break
    return copied


class Cycle:
    """Where one refresh keeps its work, and which published inputs it updates."""

    def __init__(self, as_of, *, folder=None, destination=None, readme=None, plan_path=None, releases=None,
                 first_cache=None, cycles=None, pause=None, clock=now_utc):
        self.as_of = as_of
        self.cycles = cycles or CYCLES
        self.folder = folder or self.cycles/as_of
        self.destination = destination or ROOT/'imports'
        self.readme = readme or ROOT/'README.md'
        self.plan_path = plan_path or ROOT/'data'/'import-plan.json'
        self.releases = releases or self.folder/'releases'
        self.first_cache = first_cache or FIRST_CACHE
        self.pause = pause or CAPTURE/'pause-import'  # the collector stops before its next competition while this exists
        self.clock = clock
        self.baseline, self.base, self.cache, self.staged, self.checkpoints = (
            self.folder/name for name in ('baseline', 'base', 'cache', 'staged', 'checkpoints'))
        self.state, self.note, self.log = self.folder/'state.json', self.folder/'cycle.json', self.folder/'refresh.log'

    def older_caches(self):
        """Every other cache folder: the archive's first one and those of earlier cycles."""
        others = sorted(path for path in self.cycles.glob('*/cache') if path != self.cache)
        return [*reversed(others), self.first_cache]

    def run(self, *command):
        """Run a project script, appending its output to the cycle log; return what it printed."""
        with self.log.open('a') as log:
            log.write(f"\n$ {' '.join(str(part) for part in command)}\n")
            log.flush()
            result = subprocess.run([sys.executable, *map(str, command)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=log)
            log.write(result.stdout)
        if result.returncode:
            raise DataError(f'{Path(str(command[0])).name} failed; see {self.log}')
        return result.stdout


def prepare(cycle, offline=False):
    """Freeze the baseline, read the listing again and write the cycle's plan. Returns the plan."""
    if cycle.note.exists():
        note = json.loads(cycle.note.read_text())
    else:
        published = json.loads((cycle.destination/'provenance.json').read_text(encoding='utf-8'))['coverage']
        checked_through = published.get('batch', {}).get('as_of', '')
        if cycle.as_of <= checked_through:
            raise DataError(f'The archive is already checked through {checked_through}; choose a later --as-of')
        cycle.folder.mkdir(parents=True, exist_ok=True)
        copy_bundle(cycle.destination, cycle.baseline)
        note = {'as_of': cycle.as_of, 'created_at': cycle.clock()}
        atomic_json(cycle.note, note)
    if not (cycle.base/'provenance.json').exists():
        with tempfile.TemporaryDirectory(dir=cycle.folder) as tmp:
            note['catalog_changes'] = apply_catalog(cycle.baseline, Path(tmp)/'base', Client(cycle.cache, offline))
            (Path(tmp)/'base').rename(cycle.base)
        atomic_json(cycle.note, note)
    plan = json.loads(cycle.plan_path.read_text(encoding='utf-8')) if cycle.plan_path.exists() else None
    if not (plan and plan.get('kind') == 'refresh' and plan.get('created_at') == note['created_at']):
        plan = refresh_plan(cycle.base, cycle.as_of, note['created_at'], note['catalog_changes'], plan)
        atomic_json(cycle.plan_path, plan)
    return plan


def verify_base(cycle):
    """The listing step must reproduce from the cycle's cache alone, like every other step."""
    with tempfile.TemporaryDirectory(dir=cycle.folder) as tmp:
        apply_catalog(cycle.baseline, Path(tmp)/'base', Client(cycle.cache, offline=True))
        if not same_bundle(Path(tmp)/'base', cycle.base):
            raise DataError('The refreshed listing does not replay from its cached responses')


def collect(cycle, plan, *, offline=False, recheck_sheets=False, retries=3, retry_wait=10):
    """Check every queued competition. Returns how many published match sheets were carried forward."""
    from continue_archive import transient_failure
    seeded = 0 if recheck_sheets else seed_sheets(plan, cycle.base, cycle.cache, cycle.older_caches())
    if not plan['queue']:
        # Nothing open and nothing new: the archive with the refreshed listing is the result.
        archive = History(Client(cycle.cache, offline=True))
        restore_base(archive, cycle.base)
        batch_coverage(archive, plan)
        with contextlib.redirect_stdout(io.StringIO()):
            archive.export(cycle.staged)
        return seeded
    command = [SCRIPTS/'batch_import.py', '--base', cycle.base, '--output', cycle.staged, '--plan', cycle.plan_path,
               '--cache', cycle.cache, '--checkpoint-dir', cycle.checkpoints, '--state', cycle.state, '--as-of', cycle.as_of,
               '--stop-file', cycle.pause]
    if offline:
        command.append('--offline')
    for attempt in range(retries+1):
        offset = cycle.log.stat().st_size if cycle.log.exists() else 0
        before = cycle.state.read_text() if cycle.state.exists() else ''
        with cycle.log.open('a') as log:
            code = subprocess.run([sys.executable, *map(str, command)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
        if not code:
            break
        with cycle.log.open('rb') as log:
            log.seek(offset)
            text = log.read().decode('utf-8', 'replace')
        after = cycle.state.read_text() if cycle.state.exists() else ''
        if after != before and json.loads(after).get('reason'):
            raise DataError(json.loads(after)['reason'])  # a published result changed at the source
        if attempt == retries or not transient_failure(text):
            raise DataError(f'The collector stopped; completed competitions are kept. See {cycle.log}')
        say(f'  The source did not answer; trying again in {retry_wait:g} minutes ({attempt+1}/{retries}).')
        time.sleep(retry_wait*60)
    state = json.loads(cycle.state.read_text())
    if state['state'] != 'batch_finished' or state['coverage']['pending']:
        raise DataError(f"The collector stopped with {state['coverage']['pending']} competition(s) still queued "
                        '(a pause file?); run the refresh again to continue')
    return seeded


def tidy(cycle):
    """Drop the bulky working copies of a finished cycle; keep its evidence.

    The cache (the source responses), the plan, the audit report and the log stay. The
    baseline, the staged archive and the checkpoints are copies that Git history and an
    offline replay can produce again.
    """
    shutil.copyfile(cycle.plan_path, cycle.folder/'plan.json')
    for report in cycle.releases.glob('*/audit.json'):
        shutil.copyfile(report, cycle.folder/'audit.json')
    for folder in (cycle.baseline, cycle.base, cycle.staged, cycle.checkpoints, cycle.releases):
        shutil.rmtree(folder, ignore_errors=True)


def fetched(cycle):
    """Responses retrieved during this cycle (carried-forward sheets keep their earlier date)."""
    started = json.loads(cycle.note.read_text())['created_at']
    return sum(json.loads(path.read_text())['retrieved_at'] >= started for path in cycle.cache.glob('*.json'))


def release(cycle):
    """Audit and replay the staged archive offline, then promote it into the published inputs."""
    verify_base(cycle)
    output = cycle.run(SCRIPTS/'release_batch.py', '--input', cycle.staged, '--baseline', cycle.base, '--plan', cycle.plan_path,
                       '--cache', cycle.cache, *cycle.older_caches(), '--releases', cycle.releases,
                       '--destination', cycle.destination, '--readme', cycle.readme, '--promote')
    return json.loads(output.strip().splitlines()[-1])


def refresh_rankings(cycle, offline=False):
    """Add official ranking snapshots published since the last one. Returns the importer's last line."""
    history = cycle.destination/'ranking-history'
    manifest = json.loads((history/'provenance.json').read_text(encoding='utf-8'))
    categories = sorted({r['request']['form']['agecategoryid'] for r in manifest['requests'].values()
                         if (r['request'].get('form') or {}).get('agecategoryid')}, key=int)
    latest = max(s['date'] for s in manifest['coverage']['rankings'])
    command = [SCRIPTS/'import_rankings.py', '--imports', cycle.destination, '--history', history,
               '--cache', cycle.folder/'rankings-cache', '--since', latest]
    for category in categories:
        command += ['--category', category]
    if offline:
        command.append('--offline')
    return cycle.run(*command).strip().splitlines()[0]


def refresh_standings(cycle, plan, folder=None):
    """Read the league tables again from the pages this cycle already fetched. No requests."""
    leagues = json.loads((cycle.destination/'provenance.json').read_text(encoding='utf-8'))['coverage'].get('leagues', {})
    events = [item['event'] for item in plan['queue'] if item['event'] in leagues]
    if not events:
        return 0
    command = [SCRIPTS/'import_standings.py', '--imports', cycle.destination, '--output', folder or cycle.destination/'standings',
               '--cache', cycle.cache, '--offline', '--update']
    for event in events:
        command += ['--event', event]
    cycle.run(*command)
    return len(events)


def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise DataError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def changed_paths():
    return [line[3:] for line in git('status', '--porcelain', '--untracked-files=all').splitlines()]


def unexpected(paths):
    return sorted(p for p in paths if p not in STAGED_PATHS and not p.startswith(STAGED_FOLDERS))


def check_checkout(resuming):
    """A refresh starts from the staging branch exactly, with nothing else in the working tree."""
    if git('remote', 'get-url', 'origin') != REMOTE:
        raise DataError('Remote changed')
    git('fetch', 'origin', STAGING_BRANCH)
    if git('rev-parse', 'HEAD') != git('rev-parse', f'origin/{STAGING_BRANCH}'):
        raise DataError(f'Run the refresh from a checkout at origin/{STAGING_BRANCH}, so its commit can be staged there')
    stray = unexpected(changed_paths()) if resuming else changed_paths()
    if stray:
        raise DataError(f'The working tree has other changes, first {stray[0]}; commit or set them aside before refreshing')


def stage(cycle, summary, wait_minutes=30):
    """Commit the refreshed inputs and push them to the staging branch. Nothing is published."""
    paths = changed_paths()
    if unexpected(paths):
        raise DataError(f'Unexpected paths changed, first {unexpected(paths)[0]}; nothing was committed')
    if not paths:
        say('  Nothing changed; no commit needed.')
        return None
    git('add', '--', *paths)
    git('commit', '-m', f"Refresh results through {cycle.as_of}: {summary['counts']['matches']} singles, "
                        f"{summary['checked']} competitions checked")
    commit = git('rev-parse', 'HEAD')
    git('push', 'origin', f'HEAD:{STAGING_BRANCH}')
    say(f'  Pushed {commit[:7]} to {STAGING_BRANCH}; waiting for "{VALIDATION}".')
    deadline = time.monotonic()+wait_minutes*60
    while time.monotonic() < deadline:
        listing = subprocess.run(['gh', 'run', 'list', '--commit', commit, '--limit', '10', '--json', 'name,status,conclusion'],
                                 cwd=ROOT, text=True, capture_output=True)
        runs = [r for r in json.loads(listing.stdout or '[]') if r['name'] == VALIDATION] if listing.returncode == 0 else []
        if any(r['status'] == 'completed' for r in runs):
            if any(r['conclusion'] != 'success' for r in runs):
                raise DataError(f'"{VALIDATION}" failed for {commit[:7]}; the commit is on {STAGING_BRANCH} and needs review')
            return commit
        time.sleep(20)
    raise DataError(f'Timed out waiting for "{VALIDATION}" on {commit[:7]}')


def describe(plan):
    recheck = [x for x in plan['queue'] if x.get('recheck')]
    fresh = [x for x in plan['queue'] if not x.get('recheck')]
    lines = [f"  {len(recheck)} competition(s) checked before and still open at that time",
             f"  {len(fresh)} competition(s) not checked yet",
             f"  {len(plan['deferred'])} listing(s) deferred: not started by {plan['as_of']}"]
    changes = plan.get('catalog_changes') or {}
    if changes.get('added'):
        lines.append(f"  New in the public listing: {', '.join(changes['added'])}")
    for change in changes.get('changed', []):
        lines.append(f"  Listing changed: {change['event']} {change['field']}: {change['from'] or '(empty)'} -> {change['to'] or '(empty)'}")
    return '\n'.join(lines)


def status(as_of):
    """What a refresh would queue from the listing as archived; reads nothing from the source."""
    imports = ROOT/'imports'
    coverage = json.loads((imports/'provenance.json').read_text(encoding='utf-8'))['coverage']
    plan = refresh_plan(imports, as_of, now_utc(), {'added': [], 'changed': []})
    checked = coverage.get('batch', {}).get('as_of', '')
    say(f"The archive is checked through {checked or 'an unknown date'}.")
    if as_of <= checked:
        say(f'The cutoff {as_of} is not later than that, so a refresh has nothing new to ask for yet. Still open:')
    else:
        say(f'A refresh through {as_of} would look at (before reading the public listing again):')
    say(describe(plan))
    cycles = sorted(path.name for path in CYCLES.glob('*') if (path/'cycle.json').exists())
    if cycles:
        say(f"Cycles on disk: {', '.join(cycles)}")


def run(args):
    cycle = Cycle(args.as_of)
    resuming = cycle.note.exists()
    if resuming and json.loads(cycle.note.read_text()).get('staged'):
        say(f'The refresh through {cycle.as_of} is already staged; choose a later --as-of for a new one.')
        return
    if not args.no_stage:
        check_checkout(resuming)
    say(f"{'Resuming' if resuming else 'Starting'} the refresh through {cycle.as_of} in {cycle.folder.relative_to(ROOT)}")
    plan = prepare(cycle, args.offline)
    say(describe(plan))
    collect(cycle, plan, offline=args.offline, recheck_sheets=args.recheck_sheets,
            retries=args.retries, retry_wait=args.retry_wait)
    carried = sum(1 for _ in cycle.cache.glob('*.json'))-fetched(cycle)
    say(f'  Results collected: {fetched(cycle)} source requests in this cycle, {carried} published match sheets carried forward.')
    summary = release(cycle)
    counts = summary['counts']
    say(f"  Audited, replayed and promoted: {counts['matches']} singles, {counts['doubles']} doubles, {counts['fixtures']} fixtures.")
    if not args.no_rankings:
        say('  Rankings: '+refresh_rankings(cycle, args.offline))
    if not args.no_standings:
        say(f'  Standings read again for {refresh_standings(cycle, plan)} league(s).')
    say('  Rebuilding the site and running every check.')
    cycle.run(SCRIPTS/'check_reproducible_build.py')
    cycle.run('-m', 'unittest', 'discover', '-s', 'tests')
    with cycle.log.open('a') as log:
        if subprocess.run(['node', 'tests/smoke.js'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode:
            raise DataError(f'The frontend checks failed; see {cycle.log}')
    if args.no_stage:
        say('Done. Nothing was committed (--no-stage).')
        return
    commit = stage(cycle, summary)
    atomic_json(cycle.note, {**json.loads(cycle.note.read_text()), 'staged': commit or 'unchanged'})
    tidy(cycle)
    say(f"Done. {'Staged on '+STAGING_BRANCH+' as '+commit[:7] if commit else 'Nothing to stage'}. "
        'Publishing is a separate release: python3 scripts/release.py')


def link_latest(cycle):
    """Fill a rehearsal cache with the newest cached response to every request, as links."""
    cycle.cache.mkdir(parents=True, exist_ok=True)
    for folder in reversed(cycle.older_caches()):  # oldest first, so later cycles win
        for path in folder.iterdir():
            if path.suffix in ('.json', '.body'):
                target = cycle.cache/path.name
                target.unlink(missing_ok=True)
                try:
                    target.hardlink_to(path)
                except OSError:
                    shutil.copyfile(path, target)


def rehearse(args):
    """Run a whole cycle offline in a scratch folder and compare it with the published archive.

    The source is not contacted: the newest cached responses stand in for it, so the
    refreshed archive must hold exactly the published results. Nothing in the
    repository changes. Use it after touching the refresh or collector code.
    """
    published = ROOT/'imports'
    checked = json.loads((published/'provenance.json').read_text(encoding='utf-8'))['coverage']['batch']['as_of']
    as_of = (dt.date.fromisoformat(checked)+dt.timedelta(days=1)).isoformat()
    folder = CAPTURE/'refresh-rehearsal'
    if folder.exists():
        shutil.rmtree(folder)
    cycle = Cycle(as_of, folder=folder, destination=folder/'published', readme=folder/'README.md',
                  plan_path=folder/'plan.json', releases=folder/'releases')
    folder.mkdir(parents=True)
    copy_bundle(published, cycle.destination)
    shutil.copyfile(ROOT/'README.md', cycle.readme)
    shutil.copyfile(ROOT/'data'/'import-plan.json', cycle.plan_path)
    say(f'Rehearsing a refresh through {as_of} in {folder.relative_to(ROOT)}, offline.')
    link_latest(cycle)
    plan = prepare(cycle, offline=True)
    say(describe(plan))
    collect(cycle, plan, offline=True, recheck_sheets=True)
    summary = release(cycle)
    different = [name for name in BUNDLE[:-1] if (published/name).read_bytes() != (cycle.destination/name).read_bytes()]
    say(f"  Audited and replayed {summary['checked']} competition(s) offline.")
    if different:
        raise DataError(f"The rehearsal changed {', '.join(different)}; compare {cycle.destination.relative_to(ROOT)} with imports/")
    shutil.rmtree(folder)
    say('Rehearsal passed: all seven tables are byte for byte the published ones.')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', nargs='?', choices=['run', 'rehearse'], help='omit to see what a refresh would queue')
    parser.add_argument('--as-of', default=yesterday(), help='Result cutoff, YYYY-MM-DD (default: yesterday in Athens)')
    parser.add_argument('--recheck-sheets', action='store_true', help='Fetch every match sheet again instead of carrying published ones forward')
    parser.add_argument('--offline', action='store_true', help='Use only responses already in the cycle cache')
    parser.add_argument('--no-rankings', action='store_true')
    parser.add_argument('--no-standings', action='store_true')
    parser.add_argument('--no-stage', action='store_true', help='Stop after rebuilding and testing; commit and push nothing')
    parser.add_argument('--retries', type=int, default=3, help='Retries after a source or network outage (default 3)')
    parser.add_argument('--retry-wait', type=float, default=10, help='Minutes between those retries (default 10)')
    args = parser.parse_args()
    try:
        dt.date.fromisoformat(args.as_of)
    except ValueError:
        parser.error('--as-of must be a date, YYYY-MM-DD')
    try:
        if args.command == 'run':
            run(args)
        elif args.command == 'rehearse':
            rehearse(args)
        else:
            status(args.as_of)
    except DataError as exc:
        raise SystemExit(f'Refresh stopped: {exc}')


if __name__ == '__main__':
    main()
