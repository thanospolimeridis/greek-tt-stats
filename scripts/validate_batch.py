#!/usr/bin/env python3
"""Audit a staged batch against its baseline, frozen scope and source cache."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from batch_import import RESULT_KINDS, checked_in_plan, plan_digest
from import_csv import ROOT, TYPES, DataError, build


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def audit(data, baseline, plan, *, allow_pending=False):
    """Check a staged archive against the one it grew from and against its frozen plan.

    Nothing published may be lost or altered. A refresh plan (scripts/refresh.py) names
    its only exceptions: catalog fields the source changed (catalog_changes), result
    records a reviewer let follow the source (accepted_source_changes), and source
    evidence retrieved again during the refresh itself (created_at onwards).
    """
    provenance = data['meta']['provenance']
    coverage = provenance['coverage']
    batch = coverage['batch']
    if batch['plan_sha256'] != plan_digest(plan):
        raise DataError('Release coverage does not match the frozen import plan')
    accepted = set(plan.get('accepted_source_changes', []))
    relisted = {('ttscore-'+c['event'], c['field']) for c in plan.get('catalog_changes', {}).get('changed', [])}
    if coverage.get('historical_complete') or batch.get('historical_complete'):
        raise DataError('Public traversal cannot establish complete historical coverage')

    preserved = {}
    for kind in TYPES:
        current = {r['id']: r for r in data[kind]}
        for original in baseline[kind]:
            actual = current.get(original['id'])
            if kind in RESULT_KINDS and original['id'] in accepted:
                continue  # A reviewer let this record follow the source.
            if actual is None:
                raise DataError(f'Baseline {kind} record missing: {original["id"]}')
            for field, value in original.items():
                if kind == 'events' and field == 'type':
                    continue  # Source navigation can establish the discipline.
                if kind == 'events' and (original['id'], field) in relisted:
                    continue  # The plan records this change of the public listing.
                if kind == 'players' and field == 'aliases':
                    if set(filter(None, value.split('|'))) <= set(filter(None, actual.get(field, '').split('|'))):
                        continue
                if actual.get(field, '') != value:
                    raise DataError(f'Baseline {kind} record changed: {original["id"]}.{field}')
        preserved[kind] = len(baseline[kind])
    superseded = 0
    for key, value in baseline['meta']['provenance']['requests'].items():
        actual = provenance['requests'].get(key)
        if actual == value:
            continue
        # Only a refresh may replace evidence, and only with the same request made again in its own cycle.
        if not (plan.get('created_at') and actual and actual.get('request') == value.get('request')
                and actual.get('retrieved_at', '') >= plan['created_at']):
            raise DataError(f'Baseline source evidence changed: {key}')
        superseded += 1

    queue = [r['event'] for r in plan['queue']]
    if len(queue) != len(set(queue)):
        raise DataError('Duplicate event in import plan')
    records = coverage.get('events', {})
    # Checked means checked as this plan asks: a refresh queues competitions the archive already holds.
    checked = {x['event']: records[x['event']] for x in plan['queue']
               if checked_in_plan(records.get(x['event']), x, plan['as_of'])}
    pending = [i for i in queue if i not in checked]
    if batch['eligible'] != len(queue) or batch['pending_events'] != pending or batch['pending'] != len(pending) or batch['attempted'] != len(queue)-len(pending):
        raise DataError('Batch progress does not agree with event coverage')
    if batch['deferred'] != plan['deferred']:
        raise DataError('Deferred scope changed')
    order=batch.get('processed_order',[i for i in queue if i in checked])
    if len(order)!=len(set(order)) or set(order)!=(set(queue)-set(pending)):
        raise DataError('Processed event order does not agree with checked scope')
    if pending and not allow_pending:
        raise DataError(f'{len(pending)} eligible competitions remain unchecked')
    failures = [i for i in queue if checked.get(i, {}).get('status') in ('source_access_failed', 'validation_failed')]
    if batch['failed'] != failures or failures:
        raise DataError('Batch has unresolved retrieval or validation failures')
    counts = {kind: Counter(r['event_id'].removeprefix('ttscore-') for r in data[kind]) for kind in ('matches','doubles','fixtures')}
    unprocessed=set(pending)|{item['event'] for item in plan['deferred']}
    for kind, totals in counts.items():
        original=Counter(r['event_id'].removeprefix('ttscore-') for r in baseline[kind])
        if any(totals[ident]>original[ident] for ident in unprocessed):
            raise DataError(f'New {kind} appear for an unchecked competition')
    issues = Counter(i['event'] for i in coverage['issues'])
    for ident in queue:
        if ident not in checked:
            continue
        record = checked[ident]
        for kind, field in (('matches', 'singles'), ('doubles', 'doubles'), ('fixtures', 'fixtures')):
            if record[field] != counts[kind][ident]:
                raise DataError(f'Event {ident}: {field} coverage disagrees with records')
        if record['issues'] != issues[ident]:
            raise DataError(f'Event {ident}: issue count disagrees with review records')
        if record.get('historical_complete'):
            raise DataError(f'Event {ident}: unsupported completeness claim')
        if record['categories_visited'] > record['categories_selected'] or record['categories_selected'] > record['categories_discovered']:
            raise DataError(f'Event {ident}: inconsistent category traversal')
    for item in plan['queue']:
        ident=item['event']
        if ident not in checked or item.get('scope')!='available_results':continue
        record=checked[ident]
        if (record.get('scope')!='available_results' or record.get('snapshot_date')!=plan['as_of']
                or record.get('date_status')!=item['date_status'] or record.get('status')!='partial'):
            raise DataError(f'Event {ident}: available results must retain their partial scope and cutoff')
        if any(row['date']>plan['as_of'] for kind in ('matches','doubles','fixtures')
               for row in data[kind] if row['event_id']=='ttscore-'+ident):
            raise DataError(f'Event {ident}: result after snapshot cutoff')
    for a, b in (('matches', 'doubles'), ('matches', 'fixtures'), ('doubles', 'fixtures')):
        if {r['id'] for r in data[a]} & {r['id'] for r in data[b]}:
            raise DataError(f'Game IDs overlap between {a} and {b}')
    return {'counts': {k:len(data[k]) for k in TYPES}, 'baseline_preserved':preserved,
            'eligible':len(queue), 'checked':len(queue)-len(pending), 'pending':len(pending),
            'deferred':len(plan['deferred']), 'historical_complete':False,
            'issues_by_reason':dict(Counter(i['reason'] for i in coverage['issues'])),
            'source_evidence_superseded':superseded,
            'season_coverage':data['meta']['season_coverage'],
            'dataset_sha256':data['meta']['dataset_sha256']}


def audit_cache(requests, caches):
    """Every published request must have its exact response in one of the cache folders.

    Each refresh keeps its own cache folder, so one request can exist in several with
    different retrieval times; the published metadata says which retrieval is meant.
    """
    caches = [caches] if isinstance(caches, Path) else list(caches)
    for key, expected in requests.items():
        if sha256(json.dumps(expected['request'], sort_keys=True).encode()) != key:
            raise DataError(f'Invalid request identity: {key}')
        for cache in caches:
            path = cache/f'{key}.json'
            if path.exists() and json.loads(path.read_text()) == expected:
                body = (cache/f'{key}.body').read_bytes()
                if sha256(body) == expected['sha256'] and len(body) == expected['bytes']:
                    break
        else:
            raise DataError(f'Source cache differs from published evidence: {key}')
    return len(requests)


def replay_archive(input_dir, baseline_dir, plan, cache):
    """Re-normalize cached source data, then compare one merged export byte for byte.

    A single final export avoids rewriting the growing archive after every event
    during a release check. Online collection still checkpoints every event.
    """
    import subprocess
    import sys
    import tempfile
    from batch_import import merge_event, batch_coverage
    from historical import History, restore_base
    from ttscore import Client
    manifest=json.loads((input_dir/'provenance.json').read_text())
    rebuilt=History(Client(cache,offline=True));restore_base(rebuilt,baseline_dir)
    before=dict(rebuilt.coverage.get('events',{}));leagues=set(rebuilt.coverage.get('leagues',{}))
    # Start this plan's own processing order, as the collector does before its first event.
    batch_coverage(rebuilt,plan)
    items={item['event']:item for item in plan['queue']}
    accepted=set(plan.get('accepted_source_changes',[]))
    checked=set(manifest['coverage'].get('events',{}))
    order=manifest['coverage']['batch'].get('processed_order',[item['event'] for item in plan['queue']])
    # Replay what this plan processed: new competitions, and ones a refresh checked again.
    def processed(ident):
        if ident not in checked or ident not in items:return False
        if ident in before:return not checked_in_plan(before[ident],items[ident],plan['as_of'])
        return ident not in leagues
    queue=[ident for ident in order if processed(ident)]
    available={item['event'] for item in plan['queue'] if item.get('scope')=='available_results'}
    with tempfile.TemporaryDirectory() as temporary:
        folder=Path(temporary)
        for position, ident in enumerate(queue,1):
            checkpoint=folder/f'{ident}.json'
            command=[sys.executable,str(ROOT/'scripts'/'batch_import.py'),
                '--worker',ident,'--base',str(baseline_dir),'--cache',str(cache),
                '--checkpoint-file',str(checkpoint),'--as-of',plan['as_of'],'--offline']
            if ident in available:command.append('--available-results')
            mode=manifest['coverage']['events'][ident].get('retrieval_mode')
            if mode in ('compact_brackets_v1','compact_brackets_v2'):
                command.append('--compact-brackets')
            if mode=='compact_brackets_v2':command.append('--skip-bracket-byes')
            result=subprocess.run(command,capture_output=True,text=True)
            if result.returncode:
                raise DataError(f'Cached replay failed for event {ident}: {result.stderr[-2000:]}')
            merge_event(rebuilt,json.loads(checkpoint.read_text()),ident,accepted)
            print(f'REPLAY {position}/{len(queue)}: {ident}',file=sys.stderr)
        batch_coverage(rebuilt,plan)
        import contextlib
        with contextlib.redirect_stdout(sys.stderr):rebuilt.export(folder/'archive')
        for name in [*manifest['csv_sha256'],'provenance.json']:
            if (input_dir/name).read_bytes()!=(folder/'archive'/name).read_bytes():
                raise DataError(f'Offline replay differs from release: {name}')
    return len(queue)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'capture'/'batch-imports')
    parser.add_argument('--baseline', type=Path, default=ROOT/'imports')
    parser.add_argument('--plan', type=Path, default=ROOT/'data'/'import-plan.json')
    parser.add_argument('--cache', type=Path, nargs='+', help='Also verify every referenced raw response; never publishes raw data. '
                        'The first folder is replayed; list older cache folders after it when a refresh added its own')
    parser.add_argument('--replay', action='store_true', help='Re-normalize cached events and require byte-identical CSVs and provenance; requires --cache')
    parser.add_argument('--allow-pending', action='store_true', help='Audit an intermediate checkpoint without claiming the queue is finished')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.replay and not args.cache:parser.error('--replay requires --cache')
    data = build(args.input, ROOT/'data'/'verified_events.json')
    baseline = build(args.baseline, ROOT/'data'/'verified_events.json')
    plan=json.loads(args.plan.read_text())
    report = audit(data, baseline, plan, allow_pending=args.allow_pending)
    if args.cache:
        report['source_responses_verified'] = audit_cache(data['meta']['provenance']['requests'], args.cache)
    if args.replay:
        report['offline_replayed_competitions']=replay_archive(args.input,args.baseline,plan,args.cache[0])
    output = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    print(output, end='')


if __name__ == '__main__':
    main()
