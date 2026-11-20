import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from historical import History, game_score, ko_groups, team_double
from import_csv import DataError
import test_ttscore

class HistoryTests(unittest.TestCase):
    def test_explicit_scores(self):
        row=game_score(['1','25-11-29 / 18:00','1','A - B','11-5 5-11 11-8 11-7','3 - 1'])
        self.assertEqual(row['games'],'11:5|5:11|11:8|11:7')
        self.assertEqual(row['date'],'2025-11-29')
    def test_unplayed_not_result(self):
        self.assertIsNone(game_score(['','','','','','0 - 0']))
    def test_walkover_not_invented(self):
        with self.assertRaisesRegex(DataError,'walkover_excluded'):
            game_score(['1','25-11-29 / 18:00','','A - B','W.O','3-0'])
    def test_unknown_score_is_flagged(self):
        with self.assertRaisesRegex(DataError,'unrecognized_final_score'):
            game_score(['1','25-11-29 / 18:00','','A - B','','unknown'])
    def test_game_totals_mismatch(self):
        with self.assertRaises(DataError):game_score(['1','25-11-29 / 18:00','','A - B','11-5 11-5 11-5','3-1'])
    def test_bracket_identity_binding(self):
        html='<ul class="koround"><li><a onclick="loadPlayer(24,819,1)">A</a></li><li data-gameid="99" data-groupid="42"></li><li><a onclick="loadPlayer(24,819,2)">B</a></li></ul>'
        self.assertEqual(ko_groups(html),{'42':{'99':['1','2']}})
    def test_pair_without_identity_stays_unresolved(self):
        html='<ul class="koround"><li>A / B</li><li data-gameid="99" data-groupid="42"></li><li>C / D</li></ul>'
        self.assertEqual(ko_groups(html),{'42':{'99':[None,None]}})
    def test_resolved_team_double(self):
        entry,fixture=test_ttscore.SourceTests().sample()
        entry['team_games'].update(Home_2='13',Away_2='14')
        entry['homep_2']={'AM':'113','FirstName':'C','LastName':'Test'}
        entry['awayp_2']={'AM':'114','FirstName':'D','LastName':'Test'}
        row=History(None).team_match(entry,'1',fixture,'hash','Men','1')
        self.assertEqual(row['winner_side'],'1')
        self.assertEqual(row['partner1_id'],'httf-113')
        self.assertNotIn('winner_id',row)
        self.assertEqual(row['identity_status'],'resolved_members')


class TraversalTests(unittest.TestCase):
    def test_same_abbreviation_in_different_groups_does_not_merge_players(self):
        tables=''.join(
            f'<table class="groupTable"><caption><button onclick="loadSchedule(\'{g}\')">Results</button></caption>'
            f'<tr><td><a onclick="loadPlayer(24,8,{a},0)">Same A.</a></td></tr>'
            f'<tr><td><a onclick="loadPlayer(24,8,{b},0)">Opponent B.</a></td></tr></table>'
            for g,a,b in [('100','1','2'),('200','3','4')])
        class FakeClient:
            def get(self,path,form=None):
                if '?group=' in path:
                    game='10' if 'group=100&' in path else '20'
                    return ('<script>refreshScheduleTable(0)</script>'
                            f'<table id="scheduleTable"><tr id="game-{game}"><td>1</td><td>20-01-01 / 10:00</td>'
                            '<td>1</td><td>Same A. - Opponent B.</td><td>11-5 11-5 11-5</td><td>3-0</td></tr></table>'),'scores'
                if form:return tables,'groups'
                return '<select name="agecategoryid_groups"><option value="1">Men</option></select>','selector'
        imp=History(FakeClient())
        imp.participants=lambda *args:{str(n):{'player':'p'+str(n),'team':0,'club':''} for n in range(1,5)}
        imp.counts={'categories_discovered':0,'categories_selected':0,'groups_visited':0,'singles':0,'doubles':0,'unplayed_or_bye':0}
        imp.phase('8','groups','/rounds_schedule2.php?event=8&customer=24','agecategoryid_groups')
        self.assertEqual(imp.data['matches']['ttscore-game-10']['player1_id'],'p1')
        self.assertEqual(imp.data['matches']['ttscore-game-20']['player1_id'],'p3')
        self.assertEqual(imp.coverage['issues'],[])
    def test_next_page_is_followed_and_cycles_fail(self):
        class FakeClient:
            def __init__(self):self.paths=[]
            def get(self,path,form=None):
                self.paths.append(path)
                if form is None and '?' in path and 'page=' not in path:
                    return '<select name="agecategoryid_groups"><option value="1">Men</option></select>','selector'
                return '<a onclick="nextPage(\'https://app.ttscore.io/rounds_schedule2.php?tournament=1&customer=24&page=1\')">Next</a>','body'
        client=FakeClient();imp=History(client)
        imp.participants=lambda *args:{}
        imp.counts={'categories_discovered':0,'categories_selected':0,'groups_visited':0}
        imp.phase('1','groups','/rounds_schedule2.php?event=1&customer=24','agecategoryid_groups')
        self.assertTrue(any('cyclic' in issue['reason'] for issue in imp.coverage['issues']))
        self.assertEqual(imp.counts.get('categories_visited',0),0)
        self.assertIn('/rounds_schedule2.php?tournament=1&customer=24&page=1',client.paths)
    def test_duplicate_game_not_double_counted(self):
        imp=History(None);row={'id':'a','event_id':'e','date':'2020-01-01','score1':'3','score2':'0','games':'11:5|11:5|11:5'}
        imp.put('matches',row);imp.put('matches',{**row,'phase':'consolation'})
        self.assertEqual(len(imp.data['matches']),1)
        with self.assertRaisesRegex(DataError,'conflicting'):imp.put('matches',{**row,'score2':'1'})

class IdentitySafetyTests(unittest.TestCase):
    def test_unsupported_event_reports_issue(self):
        class FakeClient:
            def get(self,*args):return '<h1>Team tournament</h1>','source'
        imp=History(FakeClient());imp.data['events']['ttscore-8']={'end_date':'2020-01-01'}
        coverage=imp.event('8')
        self.assertEqual(coverage['issues'],1)
        self.assertEqual(coverage['status'],'partial')
        self.assertFalse(coverage['historical_complete'])
    def test_public_participant_payload_is_allowlisted(self):
        import json
        class FakeClient:
            def get(self,*args):
                return json.dumps([{'ID':1,'EventID':8,'Team':0,'AM':123,'FirstName':'Test','LastName':'Athlete','clubname':'Club','Email':'private@example.org','Phone':'private','Birthday':2000,'Notes':'private'}]),'source'
        imp=History(FakeClient());mapping=imp.participants('8','1')
        self.assertEqual(mapping['1']['player'],'httf-123')
        published=json.dumps(imp.data)
        self.assertNotIn('private',published)
        self.assertNotIn('Birthday',published)
    def test_cache_failure_is_not_a_coverage_gap(self):
        from ttscore import SourceAccessError
        class FakeClient:
            def get(self,path,form=None):
                if path.startswith('/customer/24/event/'):
                    return "loadQueryResults('https://app.ttscore.io/rounds_schedule2.php?event=8&customer=24')",'source'
                raise SourceAccessError('Offline cache miss')
        imp=History(FakeClient());imp.data['events']['ttscore-8']={'end_date':'2020-01-01'}
        with self.assertRaises(SourceAccessError):imp.event('8')

if __name__=='__main__':unittest.main()
