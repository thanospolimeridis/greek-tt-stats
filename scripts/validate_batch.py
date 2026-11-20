#!/usr/bin/env python3
"""Audit a staged batch against its baseline, frozen scope and source cache."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from import_csv import ROOT, TYPES, DataError, build


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def audit(data, baseline, plan, *, allow_pending=False):
    provenance = data['meta']['provenance']
    coverage = provenance['coverage']
    batch = coverage['batch']
    expected_plan_hash = sha256((json.dumps(plan, sort_keys=True, ensure_ascii=False, indent=2)+'\n').encode())
    if batch['plan_sha256'] != expected_plan_hash:
        raise DataError('Release coverage does not match the frozen import plan')
    if coverage.get('historical_complete') or batch.get('historical_complete'):
        raise DataError('Public traversal cannot establish complete historical coverage')

    preserved = {}
    for kind in TYPES:
        current = {r['id']: r for r in data[kind]}
        for original in baseline[kind]:
            actual = current.get(original['id'])
            if actual is None:
                raise DataError(f'Baseline {kind} record missing: {original["id"]}')
            for field, value in original.items():
                if kind == 'events' and field == 'type':
                    continue  # Source navigation can establish the discipline.
                if kind == 'players' and field == 'aliases':
                    if set(filter(None, value.split('|'))) <= set(filter(None, actual.get(field, '').split('|'))):
                        continue
                if actual.get(field, '') != value:
                    raise DataError(f'Baseline {kind} record changed: {original["id"]}.{field}')
        preserved[kind] = len(baseline[kind])
    for key, value in baseline['meta']['provenance']['requests'].items():
        if provenance['requests'].get(key) != value:
            raise DataError(f'Baseline source evidence changed: {key}')

    queue = [r['event'] for r in plan['queue']]
    if len(queue) != len(set(queue)):
        raise DataError('Duplicate event in import plan')
    checked = coverage.get('events', {})
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
            'season_coverage':data['meta']['season_coverage'],
            'dataset_sha256':data['meta']['dataset_sha256']}


def audit_cache(requests, cache):
    for key, expected in requests.items():
        if sha256(json.dumps(expected['request'], sort_keys=True).encode()) != key:
            raise DataError(f'Invalid request identity: {key}')
        metadata = json.loads((cache/f'{key}.json').read_text())
        body = (cache/f'{key}.body').read_bytes()
        if metadata != expected or sha256(body) != expected['sha256'] or len(body) != expected['bytes']:
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
    prior=set(rebuilt.coverage.get('events',{}))|set(rebuilt.coverage.get('leagues',{}))
    checked=set(manifest['coverage'].get('events',{}))
    order=manifest['coverage']['batch'].get('processed_order',[item['event'] for item in plan['queue']])
    queue=[ident for ident in order if ident in checked and ident not in prior]
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
            merge_event(rebuilt,json.loads(checkpoint.read_text()),ident)
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
    parser.add_argument('--cache', type=Path, help='Also verify every referenced raw response; never publishes raw data')
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
        report['offline_replayed_competitions']=replay_archive(args.input,args.baseline,plan,args.cache)
    output = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    print(output, end='')


if __name__ == '__main__':
    main()
