import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build import build_site

class BuildTests(unittest.TestCase):
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
            self.assertEqual((root/'index.html').read_bytes(),(root/'dist'/'index.html').read_bytes())
