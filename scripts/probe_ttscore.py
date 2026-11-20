#!/usr/bin/env python3
"""Read-only, polite connectivity probe for known public TTScore event URLs.

This discovers whether direct source retrieval is possible; it does not attempt
credentials, protected endpoints, enumeration, or bypass of access controls.
Run locally when the machine has network access.
"""
import argparse
import html
import json
import re
import time
import urllib.error
import urllib.request
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
USER_AGENT='GreekTTArchiveResearch/0.1 (+read-only public-page availability check)'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--max-events',type=int,default=5,help='At most this many known event pages (default 5)')
    ap.add_argument('--delay',type=float,default=2,help='Seconds between requests (minimum 1)')
    ap.add_argument('--output',type=Path,default=ROOT/'probe-report.json')
    args=ap.parse_args()
    events=json.loads((ROOT/'data'/'verified_events.json').read_text(encoding='utf8'))
    # Parse robots rules if accessible; deny probing when robots cannot be verified.
    rp=urllib.robotparser.RobotFileParser('https://app.ttscore.io/robots.txt')
    try:
        rp.read()
        if not rp.allow_all and not rp.disallow_all and rp.mtime() is None:
            print('Could not read robots.txt; skipping automated requests.')
            return
        if rp.disallow_all:
            print('robots.txt denies automated access; stopping.')
            return
    except Exception as ex:
        print(f'robots.txt unavailable: {ex}; stopping.')
        return
    results=[]
    for event in events[:max(0,min(args.max_events,30))]:
        url=event['source_url']
        parsed=urlparse(url)
        if parsed.netloc!='app.ttscore.io' or not re.fullmatch(r'/customer/24/event/\d+',parsed.path):
            continue
        if not rp.can_fetch(USER_AGENT,url):
            results.append({'id':event['id'],'status':'robots_disallowed'})
            continue
        record={'id':event['id'],'url':url}
        try:
            req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'text/html'})
            with urllib.request.urlopen(req,timeout=15) as res:
                body=res.read(512*1024).decode('utf8',errors='replace')
                record['status']=res.status
                h1=re.search(r'<h1[^>]*>(.*?)</h1>',body,re.I|re.S)
                record['h1']=html.unescape(re.sub('<[^>]+>',' ',h1.group(1))).strip() if h1 else None
                record['has_html_tables']=bool(re.search(r'<table\b',body,re.I))
                record['mentions_xhr']=bool(re.search(r'ajax|fetch\(',body,re.I))
        except urllib.error.HTTPError as ex:
            record['status']=ex.code
            record['error']='HTTP error: no bypass attempted'
        except Exception as ex:
            record['status']='unavailable'
            record['error']=str(ex)[:180]
        results.append(record)
        time.sleep(max(1,args.delay))
    args.output.write_text(json.dumps({'target':'TTScore customer 24','results':results},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Wrote',args.output)

if __name__=='__main__':main()
