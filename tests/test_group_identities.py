import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from group_identities import score_matrices, resolve_group
from historical import History, game_score


NAMES={'1':'Same A.','2':'Other B.','3':'Same A.'}
SCORES={('1','2'):(3,0),('2','1'):(0,3),('1','3'):(3,1),('3','1'):(1,3),('2','3'):(3,1),('3','2'):(1,3)}


def matrix_html(scores=SCORES):
    html='<table class="groupTable"><button onclick="loadSchedule(\'42\')">Scores</button><tr>'
    html+=''.join(f'<th data-playerid="{p}">{p}</th>' for p in NAMES)+'</tr>'
    for p,name in NAMES.items():
        wins=sum(a>b for (home,away),(a,b) in scores.items() if home==p)
        html+=f'<tr><td><a onclick="loadPlayer(24,8,{p})">{name}</a></td>'
        html+=''.join('<td class="vs">'+('' if p==q else '-'.join(map(str,scores[p,q])))+'</td>' for q in NAMES)
        html+=f'<td class="wins">{wins}</td><td class="lost">{2-wins}</td></tr>'
    return html+'</table>'


def rows():
    return [(game,['1','20-01-01 / 10:00','1',names,points,score]) for game,names,points,score in (
        ('10','Same A. - Same A.','11-5 5-11 11-7 11-9','3-1'),
        ('20','Same A. - Other B.','11-5 11-7 11-9','3-0'),
        ('30','Other B. - Same A.','11-5 5-11 11-7 11-9','3-1'))]


class GroupIdentityTests(unittest.TestCase):
    def test_complete_reciprocal_matrix_identifies_all_three_games(self):
        matrix=score_matrices(matrix_html())['42']
        self.assertEqual(matrix,SCORES)
        self.assertEqual(resolve_group(rows(),NAMES,matrix,game_score),
                         {'10':['1','3'],'20':['1','2'],'30':['2','3']})

    def test_incomplete_or_inconsistent_tables_cannot_supply_identity(self):
        self.assertEqual(score_matrices(matrix_html().replace('class="lost">0','class="lost">1')), {})
        broken={**SCORES,('1','3'):(3,0)}
        self.assertEqual(score_matrices(matrix_html(broken)),{})
        self.assertEqual(resolve_group(rows()[:-1],NAMES,SCORES,game_score),{})
        self.assertEqual(resolve_group(rows(),NAMES,SCORES,game_score,cutoff='2019-12-31'),{})

    def test_walkovers_invalid_scores_and_duplicate_pairings_stay_unresolved(self):
        for points in ('W.O','11-10 11-5 11-5'):
            changed=rows();changed[0][1][4]=points
            self.assertEqual(resolve_group(changed,NAMES,SCORES,game_score),{})
        duplicate=rows();duplicate[2]=('40',duplicate[0][1])
        self.assertEqual(resolve_group(duplicate,NAMES,SCORES,game_score),{})

    def test_identical_scores_do_not_break_an_identity_tie(self):
        ambiguous={**SCORES,('2','3'):(0,3),('3','2'):(3,0)}
        self.assertEqual(resolve_group(rows(),NAMES,ambiguous,game_score),{})

    def test_import_recovers_only_proven_distinct_registrations(self):
        body='<script>refreshScheduleTable(0)</script><table>'
        body+=''.join(f'<tr id="game-{game}">'+''.join(f'<td>{c}</td>' for c in cells)+'</tr>' for game,cells in rows())+'</table>'
        class Client:
            def get(self,*args):return body,'detail-source'
        def importer():
            imp=History(Client());imp.counts={'singles':0}
            return imp
        people={p:{'team':0,'player':'p'+p,'club':'club'+p} for p in NAMES}
        imp=importer();imp.import_schedule('8','groups','Men','42',NAMES,people,matrix=SCORES)
        self.assertEqual(len(imp.data['matches']),3)
        self.assertEqual(imp.data['matches']['ttscore-game-10']['player2_id'],'p3')
        self.assertEqual(imp.counts['matrix_identity_resolutions'],3)
        self.assertEqual(imp.coverage['issues'],[])
        people['3']['player']='p1'
        imp=importer();imp.import_schedule('8','groups','Men','42',NAMES,people,matrix=SCORES)
        self.assertEqual(imp.data['matches'],{})
        self.assertEqual(len(imp.coverage['issues']),3)


if __name__=='__main__':unittest.main()
