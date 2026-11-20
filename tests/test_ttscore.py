"""Synthetic fixtures only: never included in the published archive."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ttscore import Client, Importer, event_rows, options, schedule_rows, DataError, SourceAccessError, digest, team_totals

class SourceTests(unittest.TestCase):
    def test_request_throttle_survives_worker_restart(self):
        clock=[100.0];starts=[]
        class Response:
            status=200
            def __init__(self,url):self.url=url
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def geturl(self):return self.url
            def read(self,*args):return b''
        def open_request(self,request,**kwargs):
            starts.append(clock[0]);return Response(request.full_url)
        with tempfile.TemporaryDirectory() as tmp,patch('ttscore.time.monotonic',side_effect=lambda:clock[0]),patch('ttscore.time.sleep',side_effect=lambda delay:clock.__setitem__(0,clock[0]+delay)),patch('urllib.request.OpenerDirector.open',open_request):
            Client(Path(tmp)).get('/robots.txt')
            clock[0]+=0.2
            Client(Path(tmp)).get('/customer/24')
        self.assertEqual(starts,[100.0,101.0])
    def test_event_epoch_is_unknown_and_source_retained(self):
        body='<div class="grid"><a href="https://app.ttscore.io/customer/24/event/123"><h4>A &amp; B</h4><h6>01/01/70-01/01/70</h6><h6>Unknown</h6></a></div>'
        row=event_rows(body,'2020-21','hash')[0]
        self.assertEqual(row['start_date'],'')
        self.assertEqual(row['name'],'A & B')
        self.assertEqual(row['source_id'],'hash')
    def test_changed_catalog_rejected(self):
        with self.assertRaises(DataError):event_rows('<h1>Sign in</h1>','2020-21','hash')
    def test_options(self):
        self.assertEqual(options('<select id="season"><option value="1"> 2020-21 </option></select>','season'),[('1','2020-21')])
        with self.assertRaises(DataError):options('','season')
    def test_schedule_schema_change(self):
        with self.assertRaises(DataError):schedule_rows('<tr id="game-1"><td>1</td></tr>')
    def test_offline_never_uses_network(self):
        with tempfile.TemporaryDirectory() as tmp, patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network')):
            with self.assertRaisesRegex(DataError,'Offline cache miss'):
                Client(Path(tmp),offline=True).get('/customer/24')
    def test_cache_hash_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)
            req={'url':'https://app.ttscore.io/robots.txt','method':'GET','form':None}
            key=digest(json.dumps(req,sort_keys=True).encode())
            (cache/f'{key}.body').write_bytes(b'tampered')
            (cache/f'{key}.json').write_text(json.dumps({'request':req,'sha256':digest(b'original')}))
            with self.assertRaisesRegex(DataError,'Corrupt cache'):Client(cache,offline=True).get('/robots.txt')
    def test_unsupported_and_write_requests_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            client=Client(Path(tmp),offline=True)
            with self.assertRaises(DataError):client.get('/admin/delete.php')
            with self.assertRaises(DataError):client.get('/game-team.php',{'game':'1'})
    def test_malformed_cache_aborts_as_access_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)
            req={'url':'https://app.ttscore.io/robots.txt','method':'GET','form':None}
            key=digest(json.dumps(req,sort_keys=True).encode())
            (cache/f'{key}.body').write_bytes(b'User-agent: *')
            for metadata in ('{broken','{}','[]'):
                (cache/f'{key}.json').write_text(metadata)
                with self.subTest(metadata=metadata),self.assertRaises(SourceAccessError):
                    Client(cache,offline=True).get('/robots.txt')
    def test_identity_uses_registration_not_names(self):
        importer=Importer(None)
        a=importer.player('123','Same Name','event1','hash')
        b=importer.player('456','Same Name','event2','hash')
        self.assertNotEqual(a,b)
        self.assertEqual(a,importer.player('123','Other Spelling','event2','hash'))
        self.assertIn('Other Spelling',importer.data['players'][a]['aliases'])
        self.assertNotEqual(importer.player('','Name','e1-1','hash'),importer.player('','Name','e2-1','hash'))
    def sample(self):
        game={'ID':'1','Home':'11','Away':'12','Home_2':'-1','Away_2':'-1','Score':'3-0','Winner':'11','Countable':'1','Winsets':'3'}
        for i in range(1,8):game.update({f'{i}H':'11' if i<=3 else '0',f'{i}A':'5' if i<=3 else '0'})
        entry={'team_games':game,'homep_1':{'AM':'111','FirstName':'A','LastName':'Test'},'awayp_1':{'AM':'112','FirstName':'B','LastName':'Test'}}
        fixture={'id':'ttscore-game-2','date':'2025-01-01','home_club_id':'c1','away_club_id':'c2'}
        return entry,fixture
    def test_fixture_totals_include_doubles(self):
        entry,_=self.sample()
        double=json.loads(json.dumps(entry));double['team_games']['Home_2']='13'
        self.assertEqual(team_totals([entry,double]),[2,0])
    def test_fixture_declared_winner_must_match(self):
        entry,_=self.sample();entry['team_games']['Winner']='12'
        with self.assertRaisesRegex(DataError,'fixture_winner'):team_totals([entry])
    def test_completed_team_match(self):
        entry,fixture=self.sample()
        row=Importer(None).team_match(entry,'1',fixture,'hash','Men','1')
        self.assertEqual(row['winner_id'],'httf-111')
        self.assertEqual(row['games'],'11:5|11:5|11:5')
        self.assertEqual(row['fixture_id'],'ttscore-game-2')
    def test_walkover_not_counted_as_played(self):
        entry,fixture=self.sample();entry['team_games']['Countable']='0'
        with self.assertRaisesRegex(DataError,'noncountable'):Importer(None).team_match(entry,'1',fixture,'hash','Men','1')
    def test_doubles_not_misrepresented_as_singles(self):
        entry,fixture=self.sample();entry['team_games']['Home_2']='13'
        with self.assertRaisesRegex(DataError,'doubles'):Importer(None).team_match(entry,'1',fixture,'hash','Men','1')
    def test_unused_lineup_not_a_result(self):
        entry,fixture=self.sample();entry['team_games']['Winner']='0'
        self.assertIsNone(Importer(None).team_match(entry,'1',fixture,'hash','Men','1'))
    def test_inconsistent_winner_rejected(self):
        entry,fixture=self.sample();entry['team_games']['Winner']='12'
        with self.assertRaisesRegex(DataError,'winner_disagrees'):Importer(None).team_match(entry,'1',fixture,'hash','Men','1')

if __name__=='__main__':unittest.main()
