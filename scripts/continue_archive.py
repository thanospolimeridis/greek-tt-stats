#!/usr/bin/env python3
"""Unattended local supervisor: collect the frozen queue in batches and publish each validated batch.

Runs until the queue is exhausted, a failure needs review, or a stop file appears. Transient
TTScore/network outages are retried after a pause; validation and any other failures stop for review.
`capture/pause-import` stops at the next competition boundary (honoured by batch_import.py) and
`capture/stop-all-imports` stops before another batch starts. Not a service or scheduled task.
This file is deliberately outside batch_import.adapter_hash(): editing it never re-normalizes events.
"""
import argparse
import collections
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build import build_site

CAPTURE=ROOT/'capture'
STOP=CAPTURE/'stop-all-imports'
PAUSE=CAPTURE/'pause-import'
STATE=CAPTURE/'supervisor-state.json'
PROGRESS=CAPTURE/'batch-progress.log'
SUPERVISOR_PID=CAPTURE/'supervisor-pid.txt'
COLLECTOR_PID=CAPTURE/'collector-pid.txt'
REMOTE='https://github.com/thanospolimeridis/greek-tt-stats.git'
SITE='https://thanospolimeridis.github.io/greek-tt-stats/'
WORKFLOWS={'Validate archive','Validate and publish static archive'}
ALLOWED={'README.md','data/catalog.json','index.html',
         *(f'imports/{k}.csv' for k in ('events','players','clubs','matches','rankings','fixtures','doubles')),
         'imports/provenance.json'}
# Collector failures that only mean the source or network was unavailable. Anything else
# (validation errors, corrupt cache, robots.txt or redirect refusals) needs human review.
TRANSIENT=re.compile(r'HTTP Error (?:429|5\d\d)\b|Network retrieval failed|Server requests a longer pause|'
                     r'TimeoutError|timed out|ConnectionResetError|RemoteDisconnected|IncompleteRead')


def transient_failure(log_text):
    return bool(TRANSIENT.search(log_text))


def read(path):return json.loads((ROOT/path).read_text())
def save(path,value):
    p=ROOT/path;t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def status(phase,**details):
    item={'phase':phase,'at':dt.datetime.now(dt.timezone.utc).isoformat(),**details}
    save(STATE,item);print(json.dumps(item,ensure_ascii=False),flush=True)
def run(*args,output=False):
    result=subprocess.run(list(args),check=True,text=True,stdout=subprocess.PIPE if output else None)
    return result.stdout.strip() if output else None


def alive(pidfile,marker,exclude=()):
    """Return the recorded pid only while that process is still the expected program."""
    try:pid=int(pidfile.read_text())
    except (OSError,ValueError):return None
    if pid in exclude:return None
    command=subprocess.run(['ps','-p',str(pid),'-o','command='],text=True,capture_output=True).stdout
    return pid if marker in command and '--worker' not in command else None


def live_check(path):
    req=urllib.request.Request(SITE+path,headers={'Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=30) as response:body=response.read()
    if body!=(ROOT/'dist'/path).read_bytes():raise RuntimeError('Live bytes differ: '+path)


def publish(batch_size):
    if run('git','branch','--show-current',output=True)!='main':raise RuntimeError('Branch changed')
    if run('git','remote','get-url','origin',output=True)!=REMOTE:raise RuntimeError('Remote changed')
    if run('git','status','--porcelain',output=True):raise RuntimeError('Working tree needs review before publishing')
    status('auditing_release')
    with (CAPTURE/'release-current.json').open('w') as out,(CAPTURE/'release-current-replay.log').open('w') as err:
        subprocess.run([sys.executable,'scripts/release_batch.py','--baseline','capture/batch-baseline',
                        '--allow-pending','--promote'],stdout=out,stderr=err,check=True)
    release=read('capture/release-current.json')
    run(sys.executable,'scripts/import_csv.py');run(sys.executable,'scripts/build.py')
    run(sys.executable,'-m','unittest','discover','-s','tests')
    run('node','tests/smoke.js');run('git','diff','--check')
    def hashes():
        files=[ROOT/'index.html',ROOT/'coverage.json',ROOT/'provenance.json',*(ROOT/'dist').rglob('*')]
        return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    before=hashes();build_site()
    if hashes()!=before:raise RuntimeError('Build is not deterministic')
    changed=set(run('git','diff','--name-only',output=True).splitlines())
    if not changed or not changed<=ALLOWED:raise RuntimeError('Unexpected release paths: '+str(changed))
    for name in changed:
        if (ROOT/name).stat().st_size>=80_000_000:raise RuntimeError('Tracked generated data needs size review: '+name)
    run('git','add','--',*sorted(changed))
    run('git','commit','-m',f'Expand archive to {release["counts"]["matches"]} singles across {release["checked"]} checked competitions')
    commit=run('git','rev-parse','HEAD',output=True)
    for attempt in range(10):
        try:run('git','push','origin','main');break
        except subprocess.CalledProcessError:
            if attempt==9:raise
            time.sleep(180)
    status('waiting_for_deployment',commit=commit,checked=release['checked'])
    deadline=time.monotonic()+1800
    while time.monotonic()<deadline:
        try:runs=json.loads(run('gh','run','list','--commit',commit,'--limit','10',
                                 '--json','databaseId,name,status,conclusion',output=True))
        except (subprocess.CalledProcessError,ValueError):
            time.sleep(20);continue
        selected=[r for r in runs if r['name'] in WORKFLOWS]
        if any(r['status']=='completed' and r['conclusion']!='success' for r in selected):
            raise RuntimeError('GitHub validation or deployment failed: '+str(selected))
        if {r['name'] for r in selected if r['conclusion']=='success'}==WORKFLOWS:break
        time.sleep(20)
    else:raise RuntimeError('Timed out waiting for GitHub deployment')
    payload=json.loads(re.search(r'<script[^>]*id="site-data"[^>]*>(.*?)</script>',
                                (ROOT/'dist/index.html').read_text(),re.S)[1])
    paths=['index.html','coverage.json','version.json']
    last=read('capture/batch-imports/provenance.json')['coverage']['batch']['processed_order'][-1]
    event_path=payload['meta']['partitions']['event'].get('ttscore-'+last)
    if event_path:
        paths.append(event_path)
        event_data=json.loads((ROOT/'dist'/event_path).read_text())
        if event_data['matches']:
            player=event_data['matches'][0]['player1_id']
            paths.append(payload['meta']['partitions']['player'][player])
    for attempt in range(8):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(live_check,paths))
            break
        except (OSError,RuntimeError):
            if attempt==7:raise
            time.sleep(20)
    c=release['counts']
    save('capture/live-check-paths.json',paths)
    save('capture/last-deploy.json',{'commit':commit,'checked':release['checked'],
         'eligible':release['checked']+release['pending'],'singles':c['matches'],'doubles':c['doubles'],
         'fixtures':c['fixtures'],'deployed_at':dt.datetime.now(dt.timezone.utc).isoformat(),
         'next_update_competitions':batch_size})
    status('deployed',commit=commit,checked=release['checked'],counts=c)


def next_batch(size):
    plan=read('data/import-plan.json');coverage=read('capture/batch-imports/provenance.json')['coverage']['batch']
    done=set(coverage['processed_order']);groups=collections.defaultdict(list)
    for item in plan['queue']:
        if item['event'] not in done:groups[item['season']].append(item)
    selected=[]
    while len(selected)<size and any(groups.values()):
        for season in sorted(groups):
            if groups[season] and len(selected)<size:selected.append(groups[season].pop(0))
    save('capture/next-batch.json',{'starting_checked':len(done),'limit':len(selected),'selected':selected})
    save('capture/active-priorities.json',[r['event'] for r in selected])
    return selected


def pause_for(seconds):
    """Sleep, but return False as soon as a stop or pause file appears."""
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if STOP.exists() or PAUSE.exists():return False
        time.sleep(5)
    return True


def detach(args):
    """Start the supervisor in its own session under caffeinate, logging to capture/supervisor.log."""
    command=['caffeinate','-is',sys.executable,str(Path(__file__).resolve()),'--batch',str(args.batch),
             '--retry-wait',str(args.retry_wait),'--max-retries',str(args.max_retries)]
    with (CAPTURE/'supervisor.log').open('a') as log:
        process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,
                                 stderr=subprocess.STDOUT,start_new_session=True)
    SUPERVISOR_PID.write_text(f'{process.pid}\n')
    print(f'Supervisor started in the background (pid {process.pid}); log: capture/supervisor.log')


def supervise(args):
    # When detached, the recorded pid is our caffeinate parent; otherwise record this process.
    if alive(SUPERVISOR_PID,'continue_archive.py')!=os.getppid():SUPERVISOR_PID.write_text(f'{os.getpid()}\n')
    # Adopt an already-running collector; never start a second one against the same cache.
    pid=alive(COLLECTOR_PID,'batch_import.py')
    if pid:
        status('waiting_for_current_batch',pid=pid)
        while alive(COLLECTOR_PID,'batch_import.py'):time.sleep(5)
    retrying=False;failures=0
    while True:
        if STOP.exists():status('stopped_by_request');return
        state=read('capture/batch-state.json')
        if state['state']!='batch_finished' and not (retrying and state['state']=='stopped_on_error'):
            raise RuntimeError('Collector needs review: '+state['state'])
        if PAUSE.exists():status('stopped_at_boundary');return
        checked=state['coverage']['attempted']
        # After an outage, keep collecting; publish at the next clean batch boundary instead.
        if not retrying and checked>read('capture/last-deploy.json')['checked']:publish(args.batch)
        selected=next_batch(args.batch)
        if not selected:status('available_queue_exhausted',historical_complete=False);return
        command=[sys.executable,'scripts/batch_import.py','--limit',str(len(selected))]
        for item in selected:command+=['--priority',item['event']]
        status('collecting',checked=checked,events=[x['event'] for x in selected])
        offset=PROGRESS.stat().st_size if PROGRESS.exists() else 0
        with PROGRESS.open('a') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
            COLLECTOR_PID.write_text(f'{process.pid}\n')
            code=process.wait()
        if code==0:
            retrying=False;failures=0;continue
        with PROGRESS.open('rb') as log:
            log.seek(offset);text=log.read().decode('utf-8','replace')
        if not transient_failure(text):
            raise RuntimeError('Collector failed; checkpoints preserved. Review capture/batch-progress.log')
        after=read('capture/batch-state.json')['coverage']['attempted']
        failures=1 if after>checked else failures+1
        if failures>args.max_retries:
            raise RuntimeError(f'Source unavailable after {failures} consecutive retries; checkpoints preserved')
        retrying=True
        status('waiting_after_source_failure',attempt=failures,minutes=args.retry_wait,checked=after)
        if not pause_for(args.retry_wait*60):
            status('stopped_by_request' if STOP.exists() else 'stopped_at_boundary',checked=after);return


def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--batch',type=int,default=50,help='Competitions collected before each validated release (default 50)')
    ap.add_argument('--retry-wait',type=float,default=20,help='Minutes to wait after a transient source/network failure (default 20)')
    ap.add_argument('--max-retries',type=int,default=6,help='Consecutive transient failures without progress before stopping (default 6)')
    ap.add_argument('--detach',action='store_true',help='Run in the background under caffeinate, independent of this terminal')
    args=ap.parse_args()
    if args.batch<1 or args.retry_wait<0 or args.max_retries<0:ap.error('Batch must be positive; retry settings non-negative')
    os.chdir(ROOT)
    other=alive(SUPERVISOR_PID,'continue_archive.py',exclude=(os.getpid(),os.getppid()))
    if other:sys.exit(f'Another supervisor is running (pid {other}); stop it before starting a new one')
    if args.detach:
        detach(args);return
    try:supervise(args)
    except Exception as exc:
        status('needs_review',reason=str(exc));raise


if __name__=='__main__':main()
