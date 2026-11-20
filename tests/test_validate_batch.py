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
