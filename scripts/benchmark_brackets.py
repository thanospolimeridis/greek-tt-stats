#!/usr/bin/env python3
"""Offline cross-check of compact brackets against already captured detail pages.

Does not fetch data, alter the cache, or publish raw participant payloads.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from compact_brackets import compact_games, bracket_byes
from historical import game_score, ko_groups
from import_csv import DataError
from ttscore import ROOT, Client, SourceAccessError, schedule_rows


def compare(manifest,cache):
    client=Client(cache,offline=True);counts=Counter();mismatches=[]
    requests=manifest['requests']
    counts['captured_source_requests']=len(requests)
    for record in requests.values():
        request=record['request']
        if request['method']!='POST' or not request['url'].endswith('/tournament_ko_games.php'):continue
        body,_=client.get('/tournament_ko_games.php',request['form'])
        counts['bracket_pages']+=1
        bindings=ko_groups(body)
        counts['bracket_groups']+=len(bindings)
        for group,candidate in bracket_byes(body).items():
            if bindings.get(group)!={candidate['game']:candidate['participants']}:continue
            try:detail,_=client.get(f'/rounds_schedule2.php?group={group}&customer=24')
            except SourceAccessError:
                counts['bye_details_not_cached']+=1;continue
            if schedule_rows(detail):
                mismatches.append({'event':request['form']['event'],'group':group,'reason':'explicit_bye_has_detail_rows'})
            else:counts['explicit_byes_with_empty_details']+=1
        for group,candidate in compact_games(body).items():
            if bindings.get(group)!={candidate['game']:candidate['participants']}:
                counts['ambiguous_groups']+=1;continue
            try:expected=game_score(candidate['cells'])
            except (DataError,ValueError):
                counts['invalid_compact_scores_fall_back']+=1;continue
            try:detail,_=client.get(f'/rounds_schedule2.php?group={group}&customer=24')
            except SourceAccessError:
                counts['details_not_cached']+=1;continue
            if 'refreshScheduleTable(0)' not in detail:
                counts['other_disciplines_fall_back']+=1;continue
            rows=schedule_rows(detail)
            try:
                if len(rows)!=1 or rows[0][0]!=candidate['game']:
                    raise DataError('detail_game_binding_differs')
                if game_score(rows[0][1])!=expected:
                    raise DataError('detail_result_differs')
            except (DataError,ValueError) as exc:
                mismatches.append({'event':request['form']['event'],'group':group,'reason':str(exc)})
            else:counts['exact_matches']+=1
    return {'counts':dict(counts),'mismatches':mismatches}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'imports'/'provenance.json')
    parser.add_argument('--cache',type=Path,default=ROOT/'capture'/'ttscore')
    args=parser.parse_args()
    report=compare(json.loads(args.input.read_text()),args.cache)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report['mismatches']:raise SystemExit(1)


if __name__=='__main__':main()
