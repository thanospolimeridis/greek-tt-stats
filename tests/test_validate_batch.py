"""Release audit rejects lost history, misleading scope and changed evidence."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_batch import audit, audit_cache, sha256
from batch_import import batch_coverage
from historical import History
from import_csv import TYPES, DataError


class ReleaseAuditTests(unittest.TestCase):
    def sample(self):
        baseline = {k:[] for k in TYPES}
        baseline['matches'] = [{'id':'old', 'event_id':'ttscore-1', 'score1':3}]
        baseline['players'] = [{'id':'p1', 'name':'Athlete', 'aliases':'Earlier Name'}]
        baseline['meta'] = {'provenance':{'requests':{}}}
        current = copy.deepcopy(baseline)
        current['matches'].append({'id':'new', 'event_id':'ttscore-2', 'score1':3})
        current['players'][0]['aliases'] += '|Another Name'
        plan = {'queue':[{'event':'2'},{'event':'3'}], 'deferred':[], 'as_of':'2026-11-20'}
        imp = History(None)
        imp.coverage['events'] = {'2':{'singles':1,'doubles':0,'fixtures':0,'issues':0,'categories_visited':1,'categories_selected':1,'categories_discovered':1,'historical_complete':False}}
        batch_coverage(imp, plan)
        current['meta'] = {'provenance':{'coverage':imp.coverage,'requests':{}}, 'season_coverage':{},'dataset_sha256':'test'}
        return current, baseline, plan

    def test_partial_release_requires_explicit_flag(self):
        current, baseline, plan = self.sample()
        with self.assertRaisesRegex(DataError, 'remain unchecked'):
            audit(current, baseline, plan)
        result = audit(current, baseline, plan, allow_pending=True)
        self.assertEqual(result['baseline_preserved']['matches'],1)
        self.assertEqual(result['pending'],1)
        self.assertFalse(result['historical_complete'])

    def test_lost_or_changed_existing_result_is_rejected(self):
        for change in ('drop','score'):
            with self.subTest(change=change):
                current, baseline, plan = self.sample()
                if change=='drop':current['matches'].pop(0)
                else:current['matches'][0]['score1']=2
                with self.assertRaisesRegex(DataError, 'Baseline matches record'):
                    audit(current, baseline, plan, allow_pending=True)

    def test_misleading_scope_or_counts_are_rejected(self):
        for change in ('pending','results','complete'):
            with self.subTest(change=change):
                current, baseline, plan = self.sample()
                coverage=current['meta']['provenance']['coverage']
                if change=='pending':coverage['batch']['pending']=0
                elif change=='results':coverage['events']['2']['singles']=2
                else:coverage['historical_complete']=True
                with self.assertRaises(DataError):
                    audit(current, baseline, plan, allow_pending=True)

    def test_uncheckpointed_results_cannot_enter_release(self):
        current, baseline, plan=self.sample()
        current['matches'].append({'id':'unchecked','event_id':'ttscore-3','score1':3})
        with self.assertRaisesRegex(DataError,'unchecked competition'):
            audit(current, baseline, plan, allow_pending=True)

    def test_replay_order_cannot_omit_or_repeat_checked_events(self):
        for order in ([],['2','2'],['3']):
            current, baseline, plan=self.sample()
            current['meta']['provenance']['coverage']['batch']['processed_order']=order
            with self.subTest(order=order), self.assertRaisesRegex(DataError,'Processed event order'):
                audit(current,baseline,plan,allow_pending=True)

    def test_active_event_requires_partial_scope_and_rejects_future_results(self):
        current,baseline,plan=self.sample()
        plan['queue'][0].update(scope='available_results',date_status='ongoing')
        coverage=current['meta']['provenance']['coverage']
        coverage['events']['2'].update(scope='available_results',date_status='ongoing',snapshot_date=plan['as_of'],status='partial')
        coverage['batch']['plan_sha256']=sha256((json.dumps(plan,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode())
        current['matches'][-1]['date']=plan['as_of']
        audit(current,baseline,plan,allow_pending=True)
        current['matches'][-1]['date']='2026-11-21'
        with self.assertRaisesRegex(DataError,'after snapshot cutoff'):audit(current,baseline,plan,allow_pending=True)
        current['matches'][-1]['date']=plan['as_of'];coverage['events']['2']['status']='public_views_traversed'
        with self.assertRaisesRegex(DataError,'partial scope'):audit(current,baseline,plan,allow_pending=True)

    def test_deferred_event_cannot_silently_gain_results(self):
        current,baseline,plan=self.sample()
        plan['deferred']=[{'event':'4','reason':'not_started_by_cutoff'}]
        current['meta']['provenance']['coverage']['batch']['deferred']=plan['deferred']
        current['meta']['provenance']['coverage']['batch']['plan_sha256']=sha256((json.dumps(plan,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode())
        current['matches'].append({'id':'future','event_id':'ttscore-4','score1':3})
        with self.assertRaisesRegex(DataError,'unchecked competition'):audit(current,baseline,plan,allow_pending=True)

    def test_cache_must_match_published_response_hash(self):
        request={'url':'https://app.ttscore.io/robots.txt','method':'GET','form':None}
        key=sha256(json.dumps(request,sort_keys=True).encode())
        body=b'User-agent: *\nAllow: /\n'
        metadata={'request':request,'sha256':sha256(body),'bytes':len(body)}
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)
            (cache/f'{key}.json').write_text(json.dumps(metadata))
            (cache/f'{key}.body').write_bytes(body)
            self.assertEqual(audit_cache({key:metadata},cache),1)
            (cache/f'{key}.body').write_bytes(body+b'changed')
            with self.assertRaisesRegex(DataError,'differs'):
                audit_cache({key:metadata},cache)


if __name__=='__main__':unittest.main()
