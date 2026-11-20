import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import re
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build import build_site

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
