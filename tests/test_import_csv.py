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

class ValidationRegressionTests(unittest.TestCase):
    setUp = ImportTests.setUp
    tearDown = ImportTests.tearDown
    import_match = ImportTests.import_match
    def test_reproducible_build(self):
        self.assertEqual(build(self.path,self.seed),build(self.path,self.seed))
    def test_invalid_finished_games(self):
        for game in ('1:0','11:10','12:8','15:12','0:0'):
            with self.subTest(game=game),self.assertRaises(DataError):parse_games(game,'test')
    def test_partial_aggregate_mismatch(self):
        m={**self.match,'score1':'2','score2':''}
        with self.assertRaisesRegex(DataError,'do not agree'):self.import_match(m)
    def test_impossible_match_score(self):
        m={**self.match,'score1':'2','score2':'1','games':''}
        with self.assertRaisesRegex(DataError,'best_of'):self.import_match(m)
    def test_games_after_decision(self):
        m={**self.match,'games':'11:5|11:5|11:5|5:11'}
        with self.assertRaisesRegex(DataError,'after match'):self.import_match(m)
    def test_duplicate_headers(self):
        (self.path/'clubs.csv').write_text('id,name,name\nc1,A,B\n')
        with self.assertRaisesRegex(DataError,'duplicate columns'):build(self.path,self.seed)
    def test_overfull_row(self):
        (self.path/'clubs.csv').write_text('id,name\nc1,A,unexpected\n')
        with self.assertRaisesRegex(DataError,'column count'):build(self.path,self.seed)
    def test_source_manifest_tampering(self):
        (self.path/'provenance.json').write_text('{"csv_sha256":{}}')
        with self.assertRaisesRegex(DataError,'hashes'):build(self.path,self.seed)
    def test_duplicate_seed_rejected(self):
        seed=json.loads(self.seed.read_text());seed.append(seed[0]);path=self.path/'seed.json';path.write_text(json.dumps(seed))
        with self.assertRaisesRegex(DataError,'duplicate'):build(self.path,path)
    def test_fixture_requires_source(self):
        row={'id':'f1','event_id':'ttscore-777','home_club_id':'c1','away_club_id':'c2','status':'completed','home_score':'4','away_score':'0'}
        write_csv(self.path,'fixtures',list(row),[row])
        with self.assertRaisesRegex(DataError,'source_url'):build(self.path,self.seed)

class DoublesValidationTests(unittest.TestCase):
    setUp = ImportTests.setUp
    tearDown = ImportTests.tearDown
    def double(self, **changes):
        row={'id':'d1','event_id':'ttscore-777','date':'2026-02-03','side1_name':'A / B','side2_name':'C / D','winner_side':'1','status':'completed','score1':'3','score2':'0','games':'11:5|11:5|11:5','source_url':'https://app.ttscore.io/test','best_of':'5',**changes}
        write_csv(self.path,'doubles',list(row),[row]);return build(self.path,self.seed)
    def test_pair_labels_do_not_create_athletes(self):
        result=self.double()
        self.assertEqual(len(result['players']),2)
        self.assertEqual(len(result['matches']),0)
        self.assertEqual(len(result['doubles']),1)
        self.assertEqual(result['meta']['events_with_results'],1)
        self.assertEqual(result['meta']['data_coverage'],'imported_match_records')
    def test_false_identity_claim_rejected(self):
        with self.assertRaisesRegex(DataError,'identity status'):
            self.double(identity_status='resolved_members')
    def test_winner_must_match_pair_score(self):
        with self.assertRaises(DataError):self.double(winner_side='2')
    def test_partial_member_identity_rejected(self):
        with self.assertRaises(DataError):self.double(player1_id='p1')
    def test_games_after_decision_rejected(self):
        with self.assertRaises(DataError):self.double(score2='1',games='11:5|11:5|11:5|5:11')
    def test_invalid_format_rejected(self):
        with self.assertRaises(DataError):self.double(best_of='4')

if __name__=='__main__':unittest.main()
