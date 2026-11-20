"""Batch safety and source-routing regressions (synthetic competition data)."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from batch_import import make_plan, merge_event, batch_coverage, catalog_fingerprint, resume_archive, prioritized_queue
from historical import History
from ttscore import DataError
import test_ttscore


class PlanTests(unittest.TestCase):
    def test_priority_preserves_scope_and_records_actual_merge_order(self):
        plan={'as_of':'2023-01-01','queue':[{'event':'1'},{'event':'2'},{'event':'3'}],'deferred':[]}
        self.assertEqual([r['event'] for r in prioritized_queue(plan,['3','3'])],['3','1','2'])
        self.assertEqual([r['event'] for r in plan['queue']],['1','2','3'])
        with self.assertRaisesRegex(DataError,'frozen eligible'):prioritized_queue(plan,['4'])
        class Client:
            def __init__(self):self.records={}
        imp=History(Client())
        for ident in ('3','1','3'):
            batch_coverage(imp,plan)
            merge_event(imp,{'data':{},'requests':{},'coverage':{'events':{ident:{}},'issues':[{'event':ident,'reason':'explicit source gap'}]},'adapter_sha256':'v1'},ident)
        self.assertEqual(batch_coverage(imp,plan)['processed_order'],['3','1'])
        self.assertEqual(batch_coverage(imp,plan)['pending_events'],['2'])
        self.assertEqual([issue['event'] for issue in imp.coverage['issues']],['3','1'])
    def test_interrupted_managed_export_recovers_without_overwriting_unmanaged_data(self):
        import contextlib
        import io
        class Client:
            def __init__(self):self.records={}
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            root=Path(tmp);baseline=root/'baseline';stage=root/'stage'
            imp=History(Client());imp.export(baseline)
            for managed in (True,False):
                imp.coverage['batch']={'runner':'ttscore-batch-v1'} if managed else {}
                imp.export(stage)
                (stage/'matches.csv').write_text('broken\n')
                if managed:
                    restored=resume_archive(Client(),stage,baseline)
                    self.assertEqual(restored.data['matches'],{})
                else:
                    with self.assertRaises(DataError):resume_archive(Client(),stage,baseline)
                self.assertEqual((stage/'matches.csv').read_text(),'broken\n')
    def test_derived_type_does_not_invalidate_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'events.csv'
            path.write_text('id,name,season,end_date\nttscore-1,Event,2020-21,2021-01-01\n')
            before=catalog_fingerprint(path)
            path.write_text('id,name,season,end_date,type\nttscore-1,Event,2020-21,2021-01-01,league\n')
            self.assertEqual(catalog_fingerprint(path),before)
            path.write_text('id,name,season,end_date,type\nttscore-1,Event,2020-21,2021-02-01,league\n')
            self.assertNotEqual(catalog_fingerprint(path),before)
    def test_round_robin_cutoff_and_existing_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rows=[('1','2020-21','2021-01-01'),('2','2020-21','2021-02-01'),
                  ('3','2021-22','2022-01-01'),('4','2021-22','2022-02-01'),
                  ('5','2022-23',''),('6','2022-23','2023-01-01'),('7','2022-23','2023-01-02')]
            with (root/'events.csv').open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['id','season','end_date']);w.writerows(('ttscore-'+i,s,d) for i,s,d in rows)
            (root/'provenance.json').write_text(json.dumps({'coverage':{'events':{'1':{}},'leagues':{}}}))
            plan=make_plan(root,'2023-01-01')
            self.assertEqual([x['event'] for x in plan['queue']],['2','3','4'])
            self.assertEqual({x['event'] for x in plan['deferred']},{'5','6','7'})
            self.assertEqual(plan['previously_processed'],['1'])
            self.assertEqual(plan,make_plan(root,'2023-01-01'))
    def test_pending_is_not_complete(self):
        imp=History(None);imp.coverage['events']={'1':{'status':'partial'}}
        plan={'as_of':'2023-01-01','queue':[{'event':'1'},{'event':'2'}],'deferred':[{'event':'3','reason':'undated'}]}
        result=batch_coverage(imp,plan)
        self.assertEqual(result['attempted'],1);self.assertEqual(result['pending_events'],['2'])
        self.assertFalse(result['historical_complete'])
    def test_merge_does_not_overwrite_athlete_identity(self):
        class Client:records={}
        imp=History(Client());imp.player('1','Current Name','x','source')
        saved={'data':{'players':{'httf-1':{'id':'httf-1','name':'Historical Name','aliases':''}}},
               'requests':{},'coverage':{'events':{'8':{}},'issues':[]},'adapter_sha256':'v1'}
        merge_event(imp,saved,'8')
        self.assertEqual(imp.data['players']['httf-1']['name'],'Current Name')
        self.assertIn('Historical Name',imp.data['players']['httf-1']['aliases'])
    def test_changed_doubles_members_are_a_conflict(self):
        imp=History(None);row={'id':'d1','event_id':'e','partner1_id':'p1','partner2_id':'p2'}
        imp.put('doubles',row)
        with self.assertRaisesRegex(DataError,'conflicting'):imp.put('doubles',{**row,'partner1_id':'p3'})


class RoutingTests(unittest.TestCase):
    def test_broken_category_does_not_hide_later_category(self):
        class Client:
            def get(self,*args):return '<select name="agecategoryid_groups"><option value="1">Broken</option><option value="2">Valid</option></select>','selector'
        imp=History(Client());imp.counts={'categories_discovered':0,'categories_selected':0}
        visited=[]
        def category(event,phase,path,field,series,cat,label):
            visited.append(cat)
            if cat=='1':raise DataError('source layout changed')
        imp.category=category
        imp.phase('8','groups','/rounds_schedule2.php?event=8&customer=24','agecategoryid_groups')
        self.assertEqual(visited,['1','2'])
        self.assertEqual(imp.counts['categories_visited'],1)
        self.assertEqual(imp.coverage['issues'][0]['category'],'Broken')
    def test_public_league_navigation_routes_to_league(self):
        class Client:
            def get(self,*args):return "loadQueryResults('https://app.ttscore.io/tournament_groups_league.php?event=8&customer=24')",'source'
        imp=History(Client());imp.data['events']['ttscore-8']={'end_date':'2020-01-01'}
        visited=[];imp.league=lambda event:visited.append(event)
        result=imp.event('8',as_of='2021-01-01')
        self.assertEqual(visited,['8']);self.assertEqual(result['phases'],['league'])
    def test_team_tournament_imports_fixture_and_rubbers(self):
        entry,_=test_ttscore.SourceTests().sample()
        class Client:
            def get(self,path,form=None):
                if path.startswith('/rounds_schedule2'):
                    return ('<script>refreshScheduleTable(2)</script><table id="scheduleTable"><tr id="game-2">'
                            '<td>1</td><td>20-01-01 / 10:00</td><td>1</td><td>Club A - Club B</td>'
                            '<td></td><td>1-0</td></tr></table>'),'schedule'
                if path.startswith('/game-team'):return '/admin/ajax/team_games.php?game=2','sheet'
                return json.dumps({'data':[entry]}),'results'
        imp=History(Client());imp.import_schedule('8','groups','Team','7',{}, {})
        self.assertEqual(len(imp.data['fixtures']),1)
        self.assertEqual(imp.data['matches']['ttscore-team-game-1']['phase'],'groups')
        self.assertEqual(imp.coverage['team_tournaments']['8']['singles_imported'],1)

if __name__=='__main__':unittest.main()
