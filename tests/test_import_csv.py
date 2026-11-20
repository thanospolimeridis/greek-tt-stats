import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from import_csv import build, DataError, parse_games
ROOT=Path(__file__).resolve().parents[1]

def write_csv(folder,name,headers,rows):
    with (folder/f'{name}.csv').open('w',encoding='utf8',newline='') as fh:
        writer=csv.DictWriter(fh,fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)
        self.seed=ROOT/'data'/'verified_events.json'
        write_csv(self.path,'clubs',['id','name'],[{'id':'c1','name':'Club A'},{'id':'c2','name':'Club B'}])
        write_csv(self.path,'players',['id','name','club_id'],[{'id':'p1','name':'Test Player A','club_id':'c1'},{'id':'p2','name':'Test Player B','club_id':'c2'}])
        self.match={'id':'m1','event_id':'ttscore-777','date':'2026-02-03','player1_id':'p1','player2_id':'p2','winner_id':'p1','status':'completed','score1':'3','score2':'1','games':'11:8|9:11|13:11|11:7','source_url':'https://app.ttscore.io/example'}
        self.headers=list(self.match)
    def tearDown(self):self.tmp.cleanup()
    def import_match(self,match):
        write_csv(self.path,'matches',self.headers,[match])
        return build(self.path,self.seed)
    def test_seed_has_only_real_event_metadata(self):
        data=build(self.path,self.seed)
        self.assertGreaterEqual(len(data['events']),10)
        self.assertEqual(data['meta']['data_coverage'],'event_catalog_only')
        self.assertEqual(len(data['matches']),0)
    def test_completed_match(self):
        data=self.import_match(self.match)
        self.assertEqual(data['matches'][0]['games'],[[11,8],[9,11],[13,11],[11,7]])
        self.assertEqual(data['meta']['verified_results'],1)
    def test_games_derive_set_score(self):
        m=self.match.copy()
        m['score1']=m['score2']=''
        data=self.import_match(m)
        self.assertEqual(data['matches'][0]['score1'],3)
        self.assertEqual(data['matches'][0]['score2'],1)
    def test_mismatch_rejected(self):
        m=self.match.copy()
        m['winner_id']='p2'
        with self.assertRaisesRegex(DataError,'winner and set score disagree'):self.import_match(m)
    def test_wrong_game_score_rejected(self):
        m=self.match.copy()
        m['games']='11:8|11:9|11:7'
        with self.assertRaisesRegex(DataError,'set score and individual games'):self.import_match(m)
    def test_missing_player_rejected(self):
        m=self.match.copy()
        m['player2_id']='missing'
        with self.assertRaisesRegex(DataError,'invalid player'):self.import_match(m)
    def test_missing_provenance_rejected(self):
        m=self.match.copy()
        m['source_url']=''
        with self.assertRaisesRegex(DataError,'needs source_url'):self.import_match(m)
    def test_html_source_rejected(self):
        m=self.match.copy()
        m['source_url']='javascript:alert(1)'
        with self.assertRaisesRegex(DataError,'Invalid public source URL'):self.import_match(m)
    def test_parser(self):
        self.assertEqual(parse_games('11-5|8:11','test'),[[11,5],[8,11]])
        with self.assertRaises(DataError):parse_games('11:11','test')
if __name__=='__main__':unittest.main()
