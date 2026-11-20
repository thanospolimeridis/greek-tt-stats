#!/usr/bin/env python3
"""Freeze, audit and optionally promote a completed import checkpoint offline."""
import argparse
import datetime as dt
import json
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

from import_csv import ROOT, TYPES, DataError, build
from validate_batch import audit, audit_cache, replay_archive, sha256


def read_bundle(folder):
    """Reject a mixed export if collection advances while files are being read."""
    manifest_bytes = (folder/'provenance.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    hashes = manifest['csv_sha256']
    if set(hashes) != {kind+'.csv' for kind in TYPES}:
        raise DataError('Release must contain exactly the seven normalized CSV tables')
    files = {name:(folder/name).read_bytes() for name in hashes}
    if (folder/'provenance.json').read_bytes() != manifest_bytes:
        raise DataError('Staged export advanced during snapshot; retry at the next checkpoint')
    if any(sha256(files[name]) != expected for name, expected in hashes.items()):
        raise DataError('Staged CSV hashes differ; export may still be in progress')
    return {**files, 'provenance.json':manifest_bytes}, manifest


def freeze_checkpoint(stage, releases):
    files, manifest = read_bundle(stage)
    checked = manifest['coverage']['batch']['attempted']
    # Include the manifest hash so corrected adapters cannot overwrite old evidence.
    destination = releases/f'{checked:04d}-{sha256(files["provenance.json"])[:16]}'
    releases.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        existing, _ = read_bundle(destination)
        if existing != files:
            raise DataError('Existing release snapshot differs; refusing to overwrite it')
        return destination
    with tempfile.TemporaryDirectory(dir=releases) as temporary:
        pending = Path(temporary)/'snapshot'
        pending.mkdir()
        for name, body in files.items():
            (pending/name).write_bytes(body)
        pending.rename(destination)
    return destination


def coverage_section(data, today):
    coverage = data['meta']['provenance']['coverage']
    batch = coverage['batch']
    counts = {kind:len(data[kind]) for kind in TYPES}
    catalog = coverage['event_catalog']['count']
    legacy = len(data['meta']['legacy_events_not_in_current_catalog'])
    competitions = len({r['event_id'] for kind in ('matches','doubles','fixtures') for r in data[kind]})
    resolved = sum(d['identity_status']=='resolved_members' for d in data['doubles'])
    unresolved = counts['doubles']-resolved
    cutoff = dt.date.fromisoformat(batch['as_of']).strftime('%-d %B %Y')
    progress = ('Collection continues through the remaining queue, with validated checkpoints published periodically.'
                if batch['pending'] else 'The eligible competition queue has been checked; source gaps and deferred listings remain.')
    return f'''## Current coverage — {today.strftime('%-d %B %Y')}

- **{catalog:,} publicly listed TTScore events**, reconciled across 2018–19 through 2026–27.
- **{legacy} additional legacy event** retained from the original prototype, labelled absent from the current catalog ({counts['events']:,} displayed total).
- **{counts['matches']:,} completed singles matches, {counts['doubles']:,} doubles matches and {counts['fixtures']:,} team fixtures**, from {competitions:,} competitions across all nine listed seasons.
- **{counts['players']:,} athletes**, linked by federation registration number where available, and **{counts['clubs']:,} exact club names**.
- **{counts['rankings']:,} ranking records**: men and women, 1 August and 1 October 2026.
- **{resolved:,} doubles matches identify all four members**; {unresolved:,} preserve source pair labels without invented athlete links.
- **{len(coverage['issues']):,} source issues** are recorded, including walkovers, unresolved fixtures and inconsistent scores. Coverage reports retain exclusion reasons and unplayed/bye counts.
- The current resumable batch has checked **{batch['attempted']:,} of {batch['eligible']:,} additional eligible competitions**. **{batch['pending']:,} remain queued**, and {len(batch['deferred']):,} listings are explicitly deferred because their dates are unknown or they had not finished by the {cutoff} cutoff.

**Historical results are incomplete.** {progress} Additional ranking snapshots also remain unimported. The season-by-season table on About shows the exact scope. No results are invented. Validation checks source consistency, not independent historical truth. The About page exposes scope and exclusions, with downloadable coverage and provenance reports.

'''


def promote(release, report, destination, readme, seed):
    files, manifest = read_bundle(release)
    data = build(release, seed)
    batch = manifest['coverage']['batch']
    if (report.get('dataset_sha256') != data['meta']['dataset_sha256']
            or report.get('provenance_sha256') != sha256(files['provenance.json'])
            or report.get('offline_replayed_competitions') != batch['attempted']):
        raise DataError('Promotion requires successful replay of this exact release')
    # Read and prepare documentation before making any changes to published inputs.
    text = readme.read_text()
    start, end = text.index('## Current coverage'), text.index('## Use and build')
    text = text[:start]+coverage_section(data, dt.datetime.now(ZoneInfo('Europe/Athens')).date())+text[end:]
    for name, body in files.items():
        target = destination/name
        temporary = target.with_suffix(target.suffix+'.tmp')
        temporary.write_bytes(body)
        temporary.replace(target)
    readme.write_text(text)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'capture'/'batch-imports')
    parser.add_argument('--baseline', type=Path, required=True, help='Original baseline, retained before any release promotion')
    parser.add_argument('--cache', type=Path, default=ROOT/'capture'/'ttscore')
    parser.add_argument('--plan', type=Path, default=ROOT/'data'/'import-plan.json')
    parser.add_argument('--releases', type=Path, default=ROOT/'capture'/'releases')
    parser.add_argument('--allow-pending', action='store_true')
    parser.add_argument('--promote', action='store_true', help='Update imports and README only after all offline release checks pass')
    args = parser.parse_args()
    release = freeze_checkpoint(args.input, args.releases)
    seed = ROOT/'data'/'verified_events.json'
    data = build(release, seed)
    baseline = build(args.baseline, seed)
    plan = json.loads(args.plan.read_text())
    report = audit(data, baseline, plan, allow_pending=args.allow_pending)
    report['source_responses_verified'] = audit_cache(data['meta']['provenance']['requests'], args.cache)
    report['offline_replayed_competitions'] = replay_archive(release, args.baseline, plan, args.cache)
    report['provenance_sha256'] = sha256((release/'provenance.json').read_bytes())
    (release/'audit.json').write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+'\n')
    if args.promote:
        promote(release, report, ROOT/'imports', ROOT/'README.md', seed)
    print(json.dumps({'release':str(release), 'promoted':args.promote, 'checked':report['checked'],
                      'pending':report['pending'], 'counts':report['counts']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
