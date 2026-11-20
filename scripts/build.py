#!/usr/bin/env python3
"""Build a portable static page without network access or JS dependencies."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_site(root=ROOT):
    data = json.loads((root/'data'/'catalog.json').read_text(encoding='utf-8'))
    # Source text must never close the JSON script element or become HTML.
    serialized = json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    css = (root/'src'/'style.css').read_text(encoding='utf-8')
    js = (root/'src'/'app.js').read_text(encoding='utf-8')
    template = (root/'src'/'template.html').read_text(encoding='utf-8')
    # Replace markers once in the template, not recursively in source data.
    import re
    replacements = {'/*INLINE_CSS*/':css,'/*INLINE_JS*/':js,'/*INLINE_JSON*/':serialized}
    html = re.sub(r'/\*INLINE_(?:CSS|JS|JSON)\*/',lambda m:replacements[m[0]],template)
    dist = root/'dist'
    dist.mkdir(exist_ok=True)
    for path in (root/'index.html', dist/'index.html'):
        temporary = path.with_suffix('.html.tmp')
        temporary.write_text(html,encoding='utf-8')
        temporary.replace(path)
    return html


if __name__ == '__main__':
    output = build_site()
    print('Built index.html and dist/index.html,',round(len(output.encode('utf-8'))/1024),'KiB')
