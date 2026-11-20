#!/usr/bin/env python3
"""Build one portable, fully self-contained index.html (zero JS dependencies)."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'data'/'catalog.json').read_text(encoding='utf-8'))
# Avoid prematurely closing <script> in inline JSON.
serialized=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
css=(ROOT/'src'/'style.css').read_text(encoding='utf-8')
js=(ROOT/'src'/'app.js').read_text(encoding='utf-8')
template=(ROOT/'src'/'template.html').read_text(encoding='utf-8')
html=template.replace('/*INLINE_CSS*/',css).replace('/*INLINE_JS*/',js).replace('/*INLINE_JSON*/',serialized)
(ROOT/'index.html').write_text(html,encoding='utf-8')
dist=ROOT/'dist'
dist.mkdir(exist_ok=True)
(dist/'index.html').write_text(html,encoding='utf-8')
print('Built index.html and dist/index.html,',round(len(html.encode('utf-8'))/1024),'KiB')
