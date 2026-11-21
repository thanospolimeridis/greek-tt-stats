import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import re
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build import build_site, club_players, match_ranks, pack_match_ranks

class BuildTests(unittest.TestCase):
    def test_hosted_partitions_preserve_results_and_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            shutil.copytree(Path(__file__).resolve().parents[1]/'src',root/'src')
            match={'id':'m1','event_id':'e1','player1_id':'p1','player2_id':'p2','status':'completed'}
            pair={'id':'d1','event_id':'e1','player1_id':'p1','partner1_id':'p3','player2_id':'p2','partner2_id':'p4'}
            fixture={'id':'f1','event_id':'e1','home_club_id':'c1','away_club_id':'c2'}
            data={'matches':[match],'doubles':[pair],'fixtures':[fixture],'meta':{'verified_results':1}}
            (root/'data'/'catalog.json').write_text(json.dumps(data))
            portable=build_site(root)
            hosted=(root/'dist'/'index.html').read_text()
            payload=json.loads(re.search(r'id="site-data">(.*?)</script>',hosted,re.S)[1])
            self.assertEqual(payload['matches'],[])
            self.assertEqual(payload['meta']['event_match_counts'],{'e1':1})
            self.assertEqual(json.loads((root/'dist'/'version.json').read_text())['release_id'],payload['meta']['release_id'])
            def part(kind,ident):
                return json.loads((root/'dist'/payload['meta']['partitions'][kind][ident]).read_text())
            self.assertEqual(part('event','e1'),{k:data[k] for k in ('matches','doubles','fixtures')})
            self.assertEqual(part('player','p1')['matches'],[match])
            self.assertEqual(part('player','p4')['matches'],[])
            self.assertEqual(part('player','p4')['doubles'],[pair])
            self.assertEqual(part('club','c2')['fixtures'],[fixture])
            self.assertNotEqual(portable,hosted)
            self.assertEqual((root/'dist'/'offline.html').read_text(),portable)
            self.assertEqual(portable,build_site(root))
            self.assertEqual(hosted,(root/'dist'/'index.html').read_text())
    def test_full_provenance_remains_downloadable_outside_page_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            shutil.copytree(Path(__file__).resolve().parents[1]/'src',root/'src')
            provenance={'requests':{'unique-request-marker':{'sha256':'abc'}},'coverage':{'historical_complete':False}}
            (root/'data'/'catalog.json').write_text(json.dumps({'meta':{'provenance':provenance}}))
            result=build_site(root)
            self.assertNotIn('unique-request-marker',result)
            self.assertEqual(json.loads((root/'dist'/'provenance.json').read_text()),provenance)
            self.assertEqual(json.loads((root/'dist'/'coverage.json').read_text()),provenance['coverage'])
            self.assertEqual((root/'provenance.json').read_bytes(),(root/'dist'/'provenance.json').read_bytes())
    def test_untrusted_source_text_cannot_break_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            shutil.copytree(Path(__file__).resolve().parents[1]/'src',root/'src')
            value='</script><script>alert(1)</script> /*INLINE_JS*/ & <b>'
            (root/'data'/'catalog.json').write_text(json.dumps({'name':value}))
            result=build_site(root)
            self.assertNotIn('</script><script>alert(1)',result)
            self.assertIn('\\u003c/script\\u003e',result)
            self.assertIn('/*INLINE_JS*/',result)  # literal source data is not substituted
            self.assertEqual(result,build_site(root))
            self.assertEqual((root/'index.html').read_bytes(),(root/'dist'/'offline.html').read_bytes())


def position(player,category,date,rank):
    return {'id':f'r-{date}-{category}-{player}','player_id':player,'category':category,'date':date,'rank':rank,'points':1.0,'source_url':'https://app.ttscore.io/test'}

def single(ident,date,first,second,status='completed'):
    return {'id':ident,'event_id':'e1','date':date,'player1_id':first,'player2_id':second,'winner_id':first,'status':status}

def ranked_catalog():
    # Synthetic: "Men" holds three players and "Boys" two of them, as senior lists hold their juniors.
    rankings=[position('p1','Men','2025-01-01',5),position('p2','Men','2025-01-01',9),position('p3','Men','2025-01-01',7),
              position('p1','Boys','2025-01-01',1),position('p2','Boys','2025-01-01',2),position('w1','Women','2025-01-01',3),
              position('p1','Men','2025-03-01',4),position('p2','Men','2025-03-01',10)]
    matches=[single('early','2024-12-31','p1','p2'),single('feb','2025-02-28','p1','p2'),single('mar','2025-03-01','p2','p1'),
             single('one','2025-01-15','px','p1'),single('none','2025-01-15','px','py'),single('mixed','2025-01-15','p1','w1'),
             single('walkover','2025-01-15','p1','p2',status='walkover')]
    return {'rankings':rankings,'matches':matches,'doubles':[],'fixtures':[],'players':[],'clubs':[],'events':[],'meta':{}}

class MatchRankTests(unittest.TestCase):
    def test_positions_come_from_the_ranking_in_force_on_the_match_day(self):
        context=match_ranks(ranked_catalog())
        self.assertEqual(context,{
            'feb':('2025-01-01','Men',5,9),   # latest snapshot before the match; widest shared list, not "Boys"
            'mar':('2025-03-01','Men',10,4),  # a snapshot published on the day counts; order follows player1/player2
            'one':('2025-01-01','Men',None,5)})  # only one player ranked: the other side stays empty
        for absent,reason in (('early','before the first snapshot'),('none','nobody ranked'),('mixed','no list in common'),('walkover','not completed')):
            self.assertNotIn(absent,context,reason)
        self.assertEqual(match_ranks({'matches':ranked_catalog()['matches']}),{})
    def test_pack_stores_dates_and_categories_once(self):
        context=match_ranks(ranked_catalog())
        self.assertEqual(pack_match_ranks(context),{'format':'match-ranks-v1','dates':['2025-01-01','2025-03-01'],'categories':['Men'],
            'rows':{'feb':[0,0,5,9],'mar':[1,0,10,4],'one':[0,0,None,5]}})
        self.assertEqual(pack_match_ranks(context,['mar','unknown']),{'format':'match-ranks-v1','dates':['2025-03-01'],'categories':['Men'],'rows':{'mar':[0,0,10,4]}})
    def test_player_files_carry_only_their_own_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            shutil.copytree(Path(__file__).resolve().parents[1]/'src',root/'src')
            (root/'data'/'catalog.json').write_text(json.dumps(ranked_catalog()))
            portable=build_site(root)
            read=lambda page:json.loads(re.search(r'id="site-data">(.*?)</script>',page,re.S)[1])
            hosted=read((root/'dist'/'index.html').read_text())
            self.assertEqual(sorted(read(portable)['match_ranks']['rows']),['feb','mar','one'])
            self.assertNotIn('match_ranks',hosted)
            part=lambda kind,ident:json.loads((root/'dist'/hosted['meta']['partitions'][kind][ident]).read_text())
            self.assertEqual(sorted(part('player','p1')['match_ranks']['rows']),['feb','mar','one'])
            self.assertEqual(part('player','px')['match_ranks']['rows'],{'one':[0,0,None,5]})
            self.assertNotIn('match_ranks',part('player','py'))
            self.assertNotIn('match_ranks',part('event','e1'))
            self.assertEqual(portable,build_site(root))


def team_single(ident,event,first,second,winner,fixture='f1',status='completed'):
    return {'id':ident,'event_id':event,'date':'2026-01-01','player1_id':first,'player2_id':second,'club1_id':'c1','club2_id':'c2',
            'winner_id':winner,'fixture_id':fixture,'status':status}

class ClubPlayerTests(unittest.TestCase):
    def matches(self):
        return [team_single('m1','e1','p1','p2','p1'),team_single('m2','e1','p1','p3','p3'),team_single('m3','e2','p1','p2','p1'),
                team_single('m4','e1','p1','p2','p1',fixture=''),          # individual event: no team fixture
                team_single('m5','e1','p1','p2','p1',status='walkover')]   # not completed
    def test_counts_completed_team_singles_per_club_event_and_player(self):
        self.assertEqual(club_players({'matches':self.matches()}),
            {'c1':[['e1','p1',2,1],['e2','p1',1,1]],'c2':[['e1','p2',1,0],['e1','p3',1,1],['e2','p2',1,0]]})
        self.assertEqual(club_players({}),{})
    def test_each_club_file_carries_only_its_own_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            shutil.copytree(Path(__file__).resolve().parents[1]/'src',root/'src')
            fixture={'id':'f1','event_id':'e1','home_club_id':'c1','away_club_id':'c2'}
            (root/'data'/'catalog.json').write_text(json.dumps({'matches':self.matches(),'doubles':[],'fixtures':[fixture],'meta':{}}))
            portable=build_site(root)
            read=lambda page:json.loads(re.search(r'id="site-data">(.*?)</script>',page,re.S)[1])
            hosted=read((root/'dist'/'index.html').read_text())
            self.assertEqual(sorted(read(portable)['club_players']),['c1','c2'])
            self.assertNotIn('club_players',hosted)
            part=lambda ident:json.loads((root/'dist'/hosted['meta']['partitions']['club'][ident]).read_text())
            self.assertEqual(part('c1')['club_players'],{'c1':[['e1','p1',2,1],['e2','p1',1,1]]})
            self.assertEqual(part('c2')['fixtures'],[fixture])
            self.assertEqual(portable,build_site(root))
