#!/usr/bin/env python3
"""Validate and checkpoint every eligible competition, with resumable season-balanced ordering."""
import argparse
import collections
import csv
import datetime as dt
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from historical import History, restore_base
from ttscore import ROOT, Client, SourceAccessError, digest
from import_csv import DataError


def adapter_hash():
    return digest(b''.join((ROOT/'scripts'/name).read_bytes() for name in
                          ('batch_import.py','historical.py','compact_brackets.py','group_identities.py','ttscore.py','import_csv.py')))


def atomic_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    tmp.replace(path)


def catalog_fingerprint(path):
    # Inferred event type changes during imports; public inventory fields do not.
    fields=('id','name','season','start_date','end_date','region','source_url','source_id','source_status')
    with path.open(encoding='utf-8') as source:
        rows=[{k:r.get(k,'') for k in fields} for r in csv.DictReader(source)]
    return digest(json.dumps(sorted(rows,key=lambda r:r['id']),sort_keys=True,ensure_ascii=False).encode())


def make_plan(base, as_of, include_available=False):
    with (base/'events.csv').open(encoding='utf-8') as source:
        rows=list(csv.DictReader(source))
    prior=json.loads((base/'provenance.json').read_text())['coverage']
    previous=set(prior.get('events',{}))|set(prior.get('leagues',{}))
    groups=collections.defaultdict(list);deferred=[]
    for row in rows:
        ident=row['id'].removeprefix('ttscore-')
        item={'event':ident,'season':row['season'],'end_date':row['end_date']}
        if ident in previous:continue
        if not row['end_date'] or row['end_date']>=as_of:
            if include_available and (not row.get('start_date') or row['start_date']<=as_of):
                groups[row['season']].append({**item,'scope':'available_results',
                    'date_status':'undated' if not row['end_date'] else 'ongoing'})
            else:
                reason=('not_started_by_cutoff' if include_available and row.get('start_date','')>as_of
                        else 'undated' if not row['end_date'] else 'not_finished_by_cutoff')
                deferred.append({**item,'reason':reason})
        else:groups[row['season']].append(item)
    for rows in groups.values():rows.sort(key=lambda x:(x['end_date'],int(x['event'])))
    queue=[]
    while any(groups.values()):
        for season in sorted(groups):
            if groups[season]:queue.append(groups[season].pop(0))
    result={'schema_version':1,'as_of':as_of,'catalog_sha256':catalog_fingerprint(base/'events.csv'),
            'previously_processed':sorted(previous,key=int),'queue':queue,'deferred':deferred,
            'historical_complete':False}
    if include_available:result.update(schema_version=2,include_available_results=True)
    return result


RESULT_KINDS=('matches','doubles','fixtures')


def checked_in_plan(record, item, as_of):
    """Whether an event's coverage record is the check this plan asks for.

    An archive plan checks every competition once, so any record satisfies it. A refresh
    plan (scripts/refresh.py) queues competitions that were checked before: an open one
    needs a snapshot at the plan's own cutoff, and one that has since finished needs a
    complete check in place of its earlier partial snapshot.
    """
    if record is None:return False
    if item.get('scope')=='available_results':
        return record.get('scope')=='available_results' and record.get('snapshot_date')==as_of
    return record.get('scope','finished')=='finished'


def merge_event(base, saved, event, accepted=()):
    """Merge only validated, event-scoped rows; preserve existing athlete identities.

    A competition that is checked again must still show every result the archive holds
    for it. A result the source has changed or no longer shows stops the merge for review;
    `accepted` lists the record IDs a reviewer allowed to follow the source (the plan's
    accepted_source_changes), which are then replaced or removed.
    """
    gone={kind:[i for i,row in base.data[kind].items() if row.get('event_id')=='ttscore-'+event
                and i not in saved['data'].get(kind,{})] for kind in RESULT_KINDS}
    refused=sorted(i for ids in gone.values() for i in ids if i not in accepted)
    if refused:
        raise DataError(f'Event {event}: {len(refused)} published record(s) are no longer in the source: '
                        f'{", ".join(refused[:20])}{" ..." if len(refused)>20 else ""}; '
                        'review, then list them under accepted_source_changes in the plan')
    for kind,ids in gone.items():
        for ident in ids:del base.data[kind][ident]
    for kind,rows in saved['data'].items():
        for ident,row in rows.items():
            if kind=='events':
                if row.get('type'):base.data[kind][ident]['type']=row['type']
            elif kind in ('players','clubs') and ident in base.data[kind]:
                if kind=='players':
                    old=base.data[kind][ident]
                    aliases=set(filter(None,old.get('aliases','').split('|')))|set(filter(None,row.get('aliases','').split('|')))
                    if row['name']!=old['name']:aliases.add(row['name'])
                    old['aliases']='|'.join(sorted(aliases-{old['name']}))
            else:
                if kind in RESULT_KINDS and ident in accepted:base.data[kind].pop(ident,None)
                try:base.put(kind,row)
                except DataError as exc:
                    if kind not in RESULT_KINDS:raise
                    raise DataError(f'Event {event}: published {kind} record {ident} differs at the source ({exc}); '
                                    'review, then list it under accepted_source_changes in the plan') from exc
    base.client.records.update(saved['requests'])
    for key in ('events','leagues','team_tournaments'):
        base.coverage.setdefault(key,{}).update(saved['coverage'].get(key,{}))
    base.coverage['issues']=[i for i in base.coverage['issues'] if i.get('event')!=event]+saved['coverage']['issues']
    base.coverage['events'][event]['adapter_sha256']=saved['adapter_sha256']
    order=base.coverage.setdefault('batch',{}).setdefault('processed_order',[])
    if event not in order:order.append(event)


def plan_digest(plan):
    return digest((json.dumps(plan,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode())


def batch_coverage(base, plan):
    ids=[x['event'] for x in plan['queue']]
    events=base.coverage.get('events',{})
    attempted=[x['event'] for x in plan['queue'] if checked_in_plan(events.get(x['event']),x,plan['as_of'])]
    done=set(attempted);fingerprint=plan_digest(plan)
    # Preserve actual merge order so prioritized imports reproduce athlete aliases
    # and the first observed identity exactly during an offline release replay.
    # The order recorded under another plan belongs to that plan's run, not to this one.
    previous=base.coverage.get('batch',{})
    order=previous.get('processed_order',[]) if previous.get('plan_sha256') in (None,fingerprint) else []
    order=[i for i in order if i in done]+[i for i in attempted if i not in order]
    positions={ident:position for position,ident in enumerate(order)}
    base.coverage['issues'].sort(key=lambda issue:positions.get(issue.get('event'),-1))
    failures=[i for i in attempted if events[i].get('status') in ('source_access_failed','validation_failed')]
    base.coverage['batch']={'runner':'ttscore-batch-v1','plan_sha256':fingerprint,
        'as_of':plan['as_of'],'eligible':len(ids),'attempted':len(attempted),'pending':len(ids)-len(attempted),
        'failed':failures,'deferred':plan['deferred'],'pending_events':[i for i in ids if i not in done],'processed_order':order,
        'historical_complete':False}
    # A refresh says so, and how many of its competitions were already in the archive.
    if plan.get('kind'):
        base.coverage['batch'].update(kind=plan['kind'],rechecked=sum(bool(x.get('recheck')) for x in plan['queue'] if x['event'] in done))
    return base.coverage['batch']


def prioritized_queue(plan, priorities):
    by_id={item['event']:item for item in plan['queue']}
    if any(ident not in by_id for ident in priorities):
        raise DataError('Priority event must already be in the frozen eligible queue')
    order=list(dict.fromkeys(priorities))
    return [by_id[ident] for ident in order]+[item for item in plan['queue'] if item['event'] not in order]


def resume_archive(client, output, baseline):
    base=History(client)
    if not (output/'provenance.json').exists():
        restore_base(base,baseline);return base
    try:
        restore_base(base,output);return base
    except (DataError,ValueError,OSError):
        manifest=json.loads((output/'provenance.json').read_text())
        if manifest.get('coverage',{}).get('batch',{}).get('runner')!='ttscore-batch-v1':raise
        print('Recovering interrupted staged export from baseline and event checkpoints',flush=True)
        base=History(client);restore_base(base,baseline);return base


def worker(args):
    ident=args.worker;out=args.checkpoint_file
    version=adapter_hash()
    if out.exists() and not args.offline:
        saved=json.loads(out.read_text())
        if (saved.get('adapter_sha256')==version and saved.get('as_of')==args.as_of
                and saved.get('available_results')==args.available_results
                and saved.get('compact_brackets',False)==args.compact_brackets
                and saved.get('skip_bracket_byes',False)==args.skip_bracket_byes):
            print(json.dumps({'event':ident,'checkpoint':'reused'}),flush=True);return
    client=Client(args.cache,args.offline)
    imp=History(client)
    imp.compact_brackets=args.compact_brackets
    imp.skip_bracket_byes=args.skip_bracket_byes
    imp.progress=lambda phase,category:print(json.dumps({'event':ident,'phase':phase,'category':category,'state':'checked_category'},ensure_ascii=False),flush=True)
    with (args.base/'events.csv').open(encoding='utf-8') as source:
        events={r['id']:{k:v for k,v in r.items() if v} for r in csv.DictReader(source)}
    if 'ttscore-'+ident not in events:raise DataError('Unknown catalog event')
    imp.data['events']={'ttscore-'+ident:events['ttscore-'+ident]}
    imp.event(ident,as_of=args.as_of,available_results=args.available_results)
    # Supply the catalog request that establishes this event's metadata.
    source=events['ttscore-'+ident]['source_id']
    manifest=json.loads((args.base/'provenance.json').read_text())
    client.records[source]=manifest['requests'][source]
    with tempfile.TemporaryDirectory() as tmp:imp.export(Path(tmp))
    atomic_json(out,{'event':ident,'adapter_sha256':version,'as_of':args.as_of,
                     'available_results':args.available_results,'compact_brackets':args.compact_brackets,'data':imp.data,
                     'skip_bracket_byes':args.skip_bracket_byes,
                     'coverage':imp.coverage,'requests':client.records})
    print(json.dumps(imp.coverage['events'][ident],ensure_ascii=False),flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',type=Path,default=ROOT/'imports')
    ap.add_argument('--output',type=Path,default=ROOT/'capture'/'batch-imports')
    ap.add_argument('--plan',type=Path,default=ROOT/'data'/'import-plan.json')
    ap.add_argument('--cache',type=Path,default=ROOT/'capture'/'ttscore')
    ap.add_argument('--checkpoint-dir',type=Path,default=ROOT/'capture'/'batch-checkpoints')
    ap.add_argument('--state',type=Path,default=ROOT/'capture'/'batch-state.json')
    ap.add_argument('--stop-file',type=Path,default=ROOT/'capture'/'pause-import')
    ap.add_argument('--as-of',default=dt.date.today().isoformat())
    ap.add_argument('--limit',type=int,help='Stop after this many newly processed competitions')
    ap.add_argument('--priority',action='append',default=[],help='Check an existing eligible event before resuming the remaining queue; repeatable')
    ap.add_argument('--include-available',action='store_true',help='For a new plan, also inspect active/undated events for explicitly dated results through the cutoff')
    ap.add_argument('--offline',action='store_true')
    ap.add_argument('--worker',help=argparse.SUPPRESS)
    ap.add_argument('--checkpoint-file',type=Path,help=argparse.SUPPRESS)
    ap.add_argument('--available-results',action='store_true',help=argparse.SUPPRESS)
    ap.add_argument('--compact-brackets',action='store_true',help=argparse.SUPPRESS)
    ap.add_argument('--skip-bracket-byes',action='store_true',help=argparse.SUPPRESS)
    args=ap.parse_args()
    if args.skip_bracket_byes and not args.compact_brackets:ap.error('Skipping bracket byes requires compact brackets')
    if args.worker:
        worker(args);return
    if args.limit is not None and args.limit<1:ap.error('--limit must be positive')
    if args.plan.exists():
        plan=json.loads(args.plan.read_text())
        if args.include_available and not plan.get('include_available_results'):
            raise DataError('Existing plan is frozen; use a new --plan path to review the expanded scope')
    else:
        plan=make_plan(args.base,args.as_of,args.include_available);atomic_json(args.plan,plan)
    if catalog_fingerprint(args.base/'events.csv')!=plan['catalog_sha256']:
        raise DataError('Catalog differs from the frozen plan; review and create a new plan')
    client=Client(args.cache,args.offline)
    base=resume_archive(client,args.output,args.base)
    accepted=set(plan.get('accepted_source_changes',[]))
    completed=0
    for item in prioritized_queue(plan,args.priority):
        ident=item['event'];version=adapter_hash()
        existing=base.coverage.get('events',{}).get(ident,{})
        compact=not existing or existing.get('retrieval_mode') in ('compact_brackets_v1','compact_brackets_v2')
        skip_byes=not existing or existing.get('retrieval_mode')=='compact_brackets_v2'
        available=item.get('scope')=='available_results'
        same_scope=checked_in_plan(existing or None,item,plan['as_of'])
        if existing.get('adapter_sha256')==version and same_scope and not args.offline:continue
        if args.stop_file.exists():break
        mode='compact-byes' if skip_byes else 'compact' if compact else 'details'
        checkpoint=args.checkpoint_dir/f'{ident}-{version[:16]}-{plan["as_of"]}-{mode}.json'
        status={'event':ident,'season':item['season'],'state':'retrieving','coverage':batch_coverage(base,plan)}
        atomic_json(args.state,status)
        print('START',ident,item['season'],flush=True)
        command=[sys.executable,str(Path(__file__).resolve()),'--worker',ident,'--base',str(args.base),
                 '--cache',str(args.cache),'--checkpoint-file',str(checkpoint),'--as-of',plan['as_of']]
        if args.offline:command.append('--offline')
        if available:command.append('--available-results')
        if compact:command.append('--compact-brackets')
        if skip_byes:command.append('--skip-bracket-byes')
        # A fresh interpreter loads the current adapter at each event boundary.
        result=subprocess.run(command)
        if result.returncode:
            atomic_json(args.state,{**status,'state':'stopped_on_error','returncode':result.returncode})
            raise DataError(f'Event {ident} failed; completed exports are preserved. Fix/retry without marking it imported.')
        saved=json.loads(checkpoint.read_text())
        # Validate the complete merged archive before replacing the previous export.
        candidate=base
        try:merge_event(candidate,saved,ident,accepted)
        except DataError as exc:
            atomic_json(args.state,{**status,'state':'stopped_on_error','reason':str(exc)})
            raise
        batch_coverage(candidate,plan)
        candidate.export(args.output)
        base=candidate
        completed+=not bool(existing)
        atomic_json(args.state,{'event':ident,'state':'checkpointed','coverage':batch_coverage(base,plan),
                               'counts':{k:len(v) for k,v in base.data.items()}})
        print('CHECKPOINT',ident,base.coverage['batch']['attempted'],'/',len(plan['queue']),flush=True)
        if args.limit and completed>=args.limit:break
    atomic_json(args.state,{'state':'batch_finished','coverage':batch_coverage(base,plan),
                           'counts':{k:len(v) for k,v in base.data.items()}})
    print(json.dumps({k:v for k,v in base.coverage['batch'].items() if k not in ('deferred','pending_events')},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
