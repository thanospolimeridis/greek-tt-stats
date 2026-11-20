#!/usr/bin/env python3
"""OPTIONAL developer investigation: inspect public TTScore network JSON responses.

Requires `pip install playwright` and `python -m playwright install chromium`.
Use only where the public page permits access. Does not bypass access barriers.
Captures public network JSON and DOM for determining an import schema. Avoid
running on authenticated pages or storing cookies/tokens in exported reports.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def main():
    from playwright.sync_api import sync_playwright
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--event',type=int,default=777)
    ap.add_argument('--output',type=Path,default=Path('capture'))
    args=ap.parse_args()
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    url=f'https://app.ttscore.io/customer/24/event/{args.event}'
    log=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(locale='el-GR')
        def on_response(response):
            if response.request.method!='GET':return
            parts=urlsplit(response.url)
            if parts.hostname!='app.ttscore.io':return
            ctype=response.headers.get('content-type','')
            if 'json' not in ctype.lower():return
            try:
                body=response.body()
                if len(body)>2_000_000:return
                # Avoid preserving credential-bearing URLs or query parameters.
                digest=hashlib.sha256(body).hexdigest()[:14]
                path=out/f'json-{digest}.json'
                parsed=json.loads(body)
                # JSON potentially contains personal records; keep private until reviewed.
                path.write_text(json.dumps(parsed,ensure_ascii=False,indent=2),encoding='utf8')
                log.append({'path':parts.path,'status':response.status,'filename':path.name,'bytes':len(body)})
            except Exception:
                pass
        page.on('response',on_response)
        response=page.goto(url,wait_until='domcontentloaded',timeout=25000)
        page.wait_for_timeout(3500)
        (out/'page.html').write_text(page.content(),encoding='utf8')
        print('Page HTTP status:',response.status if response else 'unknown')
        # Do not invoke buttons that might register participants or change state.
        browser.close()
    (out/'report.json').write_text(json.dumps({'source_path':urlsplit(url).path,'captured':log},ensure_ascii=False,indent=2),encoding='utf8')
    print('Responses:',len(log),'Output:',out)

if __name__=='__main__':main()
