import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compact_brackets import compact_games
from historical import History, game_score
from import_csv import DataError


def bracket(score='-8,7,12,11', winner=1, advance='2', date='21-12-18'):
    def side(ident, won=False):
        return f'<li class="game {"winner" if won else ""}"><div class="ko-position"><a onclick="loadPlayer(24,8,{ident})">P</a></div></li>'
    return ('<div class="panel-contents"><ul class="koround">'+side('1',winner==0)+
            f'<li data-gameid="99" data-groupid="42"><div class="game-info">{date} / 12:00 / Table:1</div></li>'+
            side('2',winner==1)+'</ul><ul class="koround"><div class="tournamentWinner ko-position">'+
            f'<a onclick="loadPlayer(24,8,{advance})">P</a><span>{score}</span></div></ul></div>')


class CompactBracketTests(unittest.TestCase):
    def test_winner_relative_deuce_scores_preserve_orientation(self):
        candidate=compact_games(bracket())['42']
        self.assertEqual(candidate['participants'],['1','2'])
        self.assertEqual(candidate['game'],'99')
        result=game_score(candidate['cells'])
        self.assertEqual(result['games'],'11:8|7:11|12:14|11:13')
        self.assertEqual((result['score1'],result['score2']),('1','3'))
        self.assertEqual(result['date'],'2021-12-18')

    def test_winning_top_player_and_zero_point_games(self):
        result=game_score(compact_games(bracket('0,-0,5,9',0,'1'))['42']['cells'])
        self.assertEqual(result['games'],'11:0|0:11|11:5|11:9')

    def test_nonstandard_or_unresolved_results_require_details(self):
        for score in ('W.O','BYE','','3 - 0','1,2','1,2,3,4,5,6,7,8'):
            with self.subTest(score=score):self.assertEqual(compact_games(bracket(score)),{})
        self.assertEqual(compact_games(bracket(advance='3')), {})
        self.assertEqual(compact_games(bracket(winner=-1)), {})
        self.assertEqual(compact_games(bracket().replace('loadPlayer(24,8,1)','')), {})

    def test_legal_termination_still_requires_normal_score_validator(self):
        candidate=compact_games(bracket('1,2,3,-4',0,'1'))['42']
        with self.assertRaisesRegex(DataError,'games_after_decision'):game_score(candidate['cells'])
        candidate=compact_games(bracket(date=''))['42']
        with self.assertRaises(ValueError):game_score(candidate['cells'])

    def test_conflicting_group_candidates_require_details(self):
        self.assertEqual(compact_games(bracket()+bracket('1,2,3')), {})

    def test_previous_round_score_is_read_from_next_column(self):
        html=bracket().replace('<li class="game ">','<li class="game "><span class="score">1,2,3</span>')
        self.assertEqual(game_score(compact_games(html)['42']['cells'])['score2'],'3')

    def test_scores_cannot_be_borrowed_from_another_placement_bracket(self):
        html=bracket(advance='3')+bracket().replace('data-gameid="99"','data-gameid="100"').replace('data-groupid="42"','data-groupid="43"')
        self.assertEqual(set(compact_games(html)),{'43'})

    def test_import_uses_bracket_provenance_and_skips_only_valid_singles(self):
        imp=History(None);imp.counts={}
        people={'1':{'team':0,'player':'p1','club':'c1'},'2':{'team':0,'player':'p2','club':'c2'}}
        candidate=compact_games(bracket())['42'];binding={'99':['1','2']}
        def attempt(c=candidate,b=binding):
            return imp.import_compact('8','knockout','Men','42',c,b,people,'bracket-hash','https://app.ttscore.io/tournament_ko_games.php?series=1&event=8&customer=24')
        self.assertTrue(attempt())
        row=imp.data['matches']['ttscore-game-99']
        self.assertEqual((row['winner_id'],row['source_id']),('p2','bracket-hash'))
        self.assertEqual(row['games'],'11:8|7:11|12:14|11:13')
        people['2']['team']=1;self.assertFalse(attempt())
        people['2']['team']=0
        self.assertFalse(attempt(b={'99':['2','1']}))
        imp.result_cutoff='2020-01-01';self.assertFalse(attempt())
        imp.result_cutoff=None
        invalid=compact_games(bracket('1,2,3,-4',0,'1'))['42']
        self.assertFalse(attempt(c=invalid))
        self.assertEqual(len(imp.data['matches']),1)


if __name__=='__main__':unittest.main()
