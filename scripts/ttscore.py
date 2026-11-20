#!/usr/bin/env python3
"""Public TTScore collection, cached replay, and conservative normalization.

Only requests observed in customer 24's public UI are supported. POST requests
are read-only search forms, never registrations or admin mutations.
"""
import argparse
import csv
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

from import_csv import DataError, TYPES, REQUIRED, build, parse_games

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://app.ttscore.io'
AGENT = 'GreekTTArchive/0.2 (public results research; cached; 1 request/second)'
VERSION = 'ttscore-public-v3'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def clean(text):
    return ' '.join(html.unescape(str(text or '')).split())


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return ''.join(c.text() if isinstance(c, Node) else c for c in self.children)

    def find(self, tag):
        for child in self.children:
            if isinstance(child, Node):
                if child.tag == tag:
                    yield child
                yield from child.find(tag)


class Document(HTMLParser):
    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(value)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in ('input','br','hr','img','meta','link','source','area','wbr'):
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def find(self, tag):
        return self.root.find(tag)


def options(body, name):
    for select in Document(body).find('select'):
        if select.attrs.get('name', select.attrs.get('id')) == name:
            return [(o.attrs['value'], clean(o.text())) for o in select.find('option')]
    raise DataError(f'Source schema changed: missing selector {name}')


class SourceAccessError(DataError):
    """Transport/cache failure must never be normalized as a source-data gap."""


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).netloc != 'app.ttscore.io':
            raise SourceAccessError('Refusing cross-origin redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self, cache, offline=False, delay=1):
        self.cache, self.offline, self.delay = cache, offline, max(1, delay)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.records = {}
        self.throttle = self.cache/'.last-request'
        try:self.last=min(time.monotonic(),float(self.throttle.read_text()))
        except (OSError,ValueError):self.last=0
        self.opener = urllib.request.build_opener(SameOriginRedirect())
        self.robot = None

    def get(self, path, form=None):
        allowed = ('/robots.txt','/customer/24','/customer_events.php','/customer_ranking.php',
                   '/tournament_groups_league.php','/game-team.php','/admin/ajax/team_games.php',
                   '/rounds_schedule2.php','/tournament_ko_games.php','/tournament_players.php',
                   '/event_schedule.php','/admin/ajax/event_schedule.php')
        url = BASE + path
        if urllib.parse.urlsplit(path).path not in allowed and not re.fullmatch(r'/customer/24/event/\d+',path):
            raise SourceAccessError(f'Unsupported public request: {path}')
        method = 'POST' if form is not None else 'GET'
        if form is not None and urllib.parse.urlsplit(path).path not in ('/customer_events.php','/customer_ranking.php','/tournament_groups_league.php','/rounds_schedule2.php','/tournament_ko_games.php','/tournament_players.php','/admin/ajax/event_schedule.php'):
            raise SourceAccessError('Only read-only search forms may use POST')
        if path != '/robots.txt' and self.robot is None:
            rules = self.get('/robots.txt')[0]
            self.robot = urllib.robotparser.RobotFileParser(BASE+'/robots.txt')
            self.robot.parse(rules.splitlines())
        if self.robot and not self.robot.can_fetch(AGENT,url):
            raise SourceAccessError(f'robots.txt disallows {path}')
        request = {'url':url,'method':method,'form':form}
        key = digest(json.dumps(request,sort_keys=True).encode())
        meta_path, body_path = self.cache/f'{key}.json', self.cache/f'{key}.body'
        if meta_path.exists() and body_path.exists():
            try:
                metadata, body = json.loads(meta_path.read_text()), body_path.read_bytes()
                if metadata['sha256'] != digest(body) or metadata['request'] != request:
                    raise SourceAccessError(f'Corrupt cache: {key}')
            except (OSError,ValueError,KeyError,TypeError) as exc:
                raise SourceAccessError(f'Corrupt cache: {key}') from exc
        else:
            if self.offline:
                raise SourceAccessError(f'Offline cache miss: {method} {path} {form}')
            for attempt in range(3):
                time.sleep(max(0, self.delay-(time.monotonic()-self.last)))
                self.last = time.monotonic()
                self.throttle.write_text(str(self.last))
                req = urllib.request.Request(url, data=urllib.parse.urlencode(form).encode() if form is not None else None,
                                             headers={'User-Agent':AGENT})
                try:
                    with self.opener.open(req, timeout=30) as response:
                        if response.geturl() != url:
                            raise SourceAccessError(f'Unexpected redirect: {path}')
                        body = response.read(5_000_001)
                        if len(body) > 5_000_000:
                            raise SourceAccessError('Response exceeds 5 MB limit')
                        metadata = {'request':request,'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                                    'sha256':digest(body),'bytes':len(body),'status':response.status}
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code not in (429,500,502,503,504) or attempt == 2:
                        raise
                    retry = exc.headers.get('Retry-After','')
                    wait = int(retry) if retry.isdigit() else 2**(attempt+1)
                    if wait > 60:
                        raise SourceAccessError('Server requests a longer pause; retry later') from exc
                    time.sleep(wait)
                except (urllib.error.URLError,TimeoutError,ConnectionError) as exc:
                    if attempt==2:
                        raise SourceAccessError(f'Network retrieval failed: {path}') from exc
                    time.sleep(2**(attempt+1))
            body_path.write_bytes(body)
            meta_path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
        self.records[key] = metadata
        try:
            return body.decode('utf-8-sig'), key
        except UnicodeDecodeError as exc:
            raise SourceAccessError(f'Invalid response encoding: {key}') from exc


def event_rows(body, season, source_id):
    rows = []
    for a in Document(body).find('a'):
        url = a.attrs.get('href','')
        match = re.fullmatch(re.escape(BASE)+r'/customer/24/event/(\d+)', url)
        if not match:
            continue
        titles, subtitles = list(a.find('h4')), list(a.find('h6'))
        if len(titles) != 1 or len(subtitles) < 2:
            raise DataError('Event card schema changed')
        dates = clean(subtitles[0].text()).split('-')
        if len(dates) != 2:
            raise DataError('Event dates schema changed')
        parsed = [dt.datetime.strptime(d,'%d/%m/%y').date().isoformat() for d in dates]
        # TTScore uses Unix epoch for unknown dates, not a 1970 tournament.
        parsed = ['' if d == '1970-01-01' else d for d in parsed]
        rows.append({'id':'ttscore-'+match[1],'name':clean(titles[0].text()),'season':season,
                     'start_date':parsed[0],'end_date':parsed[1], 'region':clean(subtitles[1].text()),
                     'source_url':url,'source_status':'retrieved_event_metadata','source_id':source_id})
    if not rows and 'grid' not in body:
        raise DataError('Event catalog response is not an event grid')
    return rows


def schedule_rows(body):
    result=[]
    for tr in Document(body).find('tr'):
        match = re.fullmatch(r'game-(\d+)',tr.attrs.get('id',''))
        if match:
            cells = [clean(td.text()) for td in tr.find('td')]
            if len(cells) != 6:
                raise DataError('Source schedule schema changed')
            result.append((match[1],cells))
    if not result and 'scheduleTable' not in body:
        raise DataError('Missing source schedule table')
    return result


def team_totals(entries):
    """Cross-check a fixture using declared winners, including doubles."""
    total = [0, 0]
    for entry in entries:
        game = entry['team_games']
        if not game.get('Score') or game.get('Winner') in (None, '', '0', '-1'):
            continue
        score = re.fullmatch(r'(\d+)-(\d+)', game['Score'])
        if not score or str(game['Countable']) != '1':
            raise DataError('fixture_nonstandard_result_requires_review')
        a, b = map(int, score.groups())
        target = int(game['Winsets'])
        if max(a,b) != target or min(a,b) >= target:
            raise DataError('fixture_unfinished_result_requires_review')
        side = 0 if a > b else 1
        if game['Winner'] != game['Home' if side == 0 else 'Away']:
            raise DataError('fixture_winner_disagrees')
        total[side] += 1
    return total


class Importer:
    def __init__(self, client):
        self.client=client
        self.data={k:{} for k in TYPES}
        self.coverage={'historical_complete':False,'event_catalog':'not_requested','leagues':{},'rankings':[],'issues':[]}

    def put(self, kind, row):
        old=self.data[kind].get(row['id'])
        if old and old != row:
            raise DataError(f'Conflicting {kind} ID {row["id"]}')
        self.data[kind][row['id']]=row

    def club(self, name):
        name=clean(name)
        if not name:
            return ''
        ident='club-name-'+digest(name.encode())[:16]
        self.data['clubs'][ident]={'id':ident,'name':name,'identity_basis':'exact_source_name'}
        return ident

    def player(self, number, name, scope, source_id, club_id='', club_date=''):
        name=clean(name)
        number=clean(number)
        ident='httf-'+number if number and number.isdigit() and int(number)>0 else 'ttscore-local-'+scope
        row=self.data['players'].get(ident, {'id':ident,'name':name,'aliases':'','source_id':source_id,
                                            'identity_basis':'federation_registration' if ident.startswith('httf-') else 'event_local'})
        if name != row['name']:
            row['aliases']='|'.join(sorted(set(filter(None,row['aliases'].split('|')))|{name}))
        if club_id and club_date >= row.get('club_as_of',''):
            row.update(club_id=club_id,club_as_of=club_date)
        self.data['players'][ident]=row
        return ident

    def catalog(self):
        home,_=self.client.get('/customer/24')
        if 'customer_events.php?customer=24' not in home:
            raise DataError('Customer page no longer links event search')
        selector,_=self.client.get('/customer_events.php?customer=24')
        seasons=[(v,n) for v,n in options(selector,'select-season') if v]
        allbody,allsource=self.client.get('/customer_events.php',{'customer':'24','season':'','getStats':'1'})
        allids={r['id'] for r in event_rows(allbody,'unknown',allsource)}
        for value,season in seasons:
            body,key=self.client.get('/customer_events.php',{'customer':'24','season':value,'getStats':'1'})
            for row in event_rows(body,season,key):
                self.put('events',row)
        if set(self.data['events']) != allids:
            raise DataError('All-seasons listing disagrees with union of season listings')
        self.coverage['event_catalog']={'status':'reconciled_public_listing','count':len(allids),'seasons':[s for _,s in seasons],
                                        'scope':'Only currently exposed customer 24 events; deleted/unlisted events unknown'}

    def league(self, event):
        if 'ttscore-'+event not in self.data['events']:
            raise DataError('League event must be in retrieved public catalog')
        self.data['events']['ttscore-'+event]['type']='league'
        page,key=self.client.get(f'/tournament_groups_league.php?event={event}&customer=24')
        cats=options(page,'agecategoryid_league')
        summary={'status':'partial','fixtures_discovered':0,'fixtures_imported':0,'singles_imported':0,'excluded_rows':0,'unused_rows':0,'review_rows':0}
        self.coverage['leagues'][event]=summary
        for cat,category in cats:
            body,key=self.client.get('/tournament_groups_league.php',{'event':event,'customer':'24','getStats':'1','agecategoryid_league':cat})
            groups=sorted(set(re.findall(r"loadSchedule\('(\d+)'",body)))
            if not groups:
                self.coverage['issues'].append({'event':event,'reason':'no_league_groups','category':category})
            for group in groups:
                source=f'{BASE}/tournament_groups_league.php?group={group}&customer=24'
                body,key=self.client.get(source[len(BASE):])
                for game,cells in schedule_rows(body):
                    try:
                        self.fixture(event,game,cells,key,source,category,summary)
                    except SourceAccessError:raise
                    except (DataError,ValueError,KeyError,TypeError) as exc:
                        summary['review_rows']+=1
                        self.coverage['issues'].append({'event':event,'game':game,'reason':str(exc),'source_id':key})
        # Traversal does not prove historical completeness or explain absent scores.
        summary['status']='retrieved_public_league_rows'

    def fixture(self,event,game,cells,key,source,category,summary,phase=None):
        summary['fixtures_discovered']+=1
        fixture_id='ttscore-game-'+game
        if fixture_id in self.data['fixtures']:
            return
        names=cells[3].split(' - ')
        score=re.fullmatch(r'(\d+)\s*-\s*(\d+)',cells[5])
        if len(names)!=2 or not score or max(map(int,score.groups()))==0:
            self.coverage['issues'].append({'event':event,'game':game,'reason':'unresolved_or_unplayed_fixture'})
            return
        date=dt.datetime.strptime(cells[1].split(' / ')[0],'%y-%m-%d').date().isoformat()
        clubs=[self.club(n) for n in names]
        if not getattr(self,'sheet_checked',False):
            detail,_=self.client.get(f'/game-team.php?game={game}&customer=24')
            if '/admin/ajax/team_games.php?game=' not in detail:
                raise DataError('Missing public team results link')
            self.sheet_checked=True
        raw,rawkey=self.client.get(f'/admin/ajax/team_games.php?game={game}&customer=24')
        payload=json.loads(raw)
        if not isinstance(payload.get('data'),list):
            raise DataError('Missing team games data array')
        try:
            if team_totals(payload['data']) != list(map(int,score.groups())):
                raise DataError('fixture_total_disagrees_with_match_sheet')
        except DataError as exc:
            self.coverage['issues'].append({'event':event,'game':game,'reason':str(exc),'source_id':rawkey})
            return
        fixture={'id':fixture_id,'event_id':'ttscore-'+event,'date':date,'home_club_id':clubs[0],
                 'away_club_id':clubs[1],'status':'completed','home_score':score[1],'away_score':score[2],
                 'source_url':source,'source_id':key}
        self.put('fixtures',fixture)
        summary['fixtures_imported']+=1
        for entry in payload['data']:
            try:
                row=self.team_match(entry,event,fixture,rawkey,category,cells[0])
                if row:
                    if phase:row['phase']=phase
                    self.put('doubles' if 'winner_side' in row else 'matches',row)
                    summary['singles_imported']+= 'winner_side' not in row
                    summary['doubles_imported']=summary.get('doubles_imported',0)+('winner_side' in row)
                else:
                    summary['excluded_rows']+=1
                    summary['unused_rows']+=1
            except (DataError,ValueError,KeyError,TypeError) as exc:
                summary['excluded_rows']+=1
                summary['review_rows']+=1
                self.coverage['issues'].append({'event':event,'game':game,'row':entry.get('team_games',{}).get('ID'),
                                               'reason':str(exc),'source_id':rawkey})

    def team_match(self, entry,event,fixture,source_id,category,round_):
        game=entry['team_games']
        is_double = int(game['Home_2'] or -1)>0 or int(game['Away_2'] or -1)>0
        if int(game['Home'] or 0)<=0 or int(game['Away'] or 0)<=0:
            return None  # bye / unset lineup, not a played match
        if not game.get('Score') or game.get('Winner') in (None,'','0','-1'):
            return None  # unused slots, schedules and unfinished games
        if str(game['Countable']) != '1':
            raise DataError('walkover_or_noncountable_requires_review')
        score=re.fullmatch(r'(\d+)-(\d+)',game['Score'])
        if not score:
            raise DataError('invalid_team_match_score')
        scores=list(map(int,score.groups()))
        target=int(game['Winsets'])
        if max(scores)!=target or min(scores)>=target:
            raise DataError('unfinished_or_invalid_score')
        games=[]
        ended=False
        for i in range(1,8):
            a,b=int(game.get(f'{i}H') or 0),int(game.get(f'{i}A') or 0)
            if (a,b)==(0,0):
                ended=True
            else:
                if ended:
                    raise DataError('noncontiguous_game_scores')
                games.append(f'{a}:{b}')
        parsed=parse_games('|'.join(games),'TTScore '+game['ID'])
        if [sum(a>b for a,b in parsed),sum(b>a for a,b in parsed)] != scores:
            raise DataError('set_totals_disagree')
        winner='Home' if scores[0]>scores[1] else 'Away'
        if game['Winner']!=game[winner]:
            raise DataError('winner_disagrees')
        players=[]
        for side,key,club in [('Home','homep_1',fixture['home_club_id']),('Away','awayp_1',fixture['away_club_id'])]:
            p=entry[key]
            name=clean((p['LastName'] or '')+' '+(p['FirstName'] or ''))
            if not name:
                raise DataError('missing_player_name')
            players.append(self.player(p['AM'],name,event+'-'+game[side],source_id))
        if is_double:
            from historical import team_double
            return team_double(self,entry,event,fixture,source_id,category,round_,players,games,scores,target)
        return {'id':'ttscore-team-game-'+game['ID'],'event_id':'ttscore-'+event,'date':fixture['date'],
                'player1_id':players[0],'player2_id':players[1],'winner_id':players[0 if winner=='Home' else 1],
                'status':'completed','score1':str(scores[0]),'score2':str(scores[1]),'games':'|'.join(games),
                'best_of':str(2*target-1),'round':round_,'category':category,'fixture_id':fixture['id'],
                'club1_id':fixture['home_club_id'],'club2_id':fixture['away_club_id'],
                'source_url':BASE+'/game-team.php?game='+fixture['id'].removeprefix('ttscore-game-')+'&customer=24',
                'source_id':source_id}

    def ranking(self, category_id, requested_date):
        body,key=self.client.get('/customer_ranking.php?customer=24')
        cats=dict(options(body,'agecategoryid'))
        dates=dict(options(body,'select-date'))
        if category_id not in cats:
            raise DataError('Ranking category not present in selector')
        chosen='0' if requested_date=='latest' else requested_date
        if chosen not in dates:
            raise DataError('Ranking date not present in selector')
        date=re.search(r'\d{4}-\d{2}-\d{2}',dates[chosen])[0]
        body,key=self.client.get('/customer_ranking.php',{'customer':'24','getStats':'1','select-date':chosen,'agecategoryid':category_id})
        count=0
        for tr in Document(body).find('tr'):
            cells=[clean(td.text()) for td in tr.find('td')]
            if not cells:
                continue
            if len(cells)!=8 or not cells[0].isdigit() or not cells[2].isdigit() or not cells[3]:
                raise DataError('Malformed ranking row; snapshot rejected')
            club=self.club(cells[4])
            player=self.player(cells[2],cells[3],cells[2],key,club,date)
            self.put('rankings',{'id':f'httf-ranking-{date}-{category_id}-{cells[2]}','player_id':player,'category':cats[category_id],
                                 'date':date,'rank':cells[0],'points':cells[7],'club_id':club,
                                 'source_url':BASE+'/customer_ranking.php?customer=24','source_id':key})
            count+=1
        if not count:
            raise DataError('Empty ranking snapshot')
        self.coverage['rankings'].append({'category':cats[category_id],'date':date,'rows':count,'source_id':key})

    def export(self, out):
        import tempfile
        out.mkdir(parents=True,exist_ok=True)
        if any(out.glob('*.csv')) and not (out/'provenance.json').exists():
            raise DataError('Refusing to overwrite manually maintained CSV imports')
        with tempfile.TemporaryDirectory() as tmp:
            staging=Path(tmp)
            for kind in TYPES:
                rows=sorted(self.data[kind].values(),key=lambda r:r['id'])
                columns=list(REQUIRED[kind])+sorted(set().union(*(set(r) for r in rows))-set(REQUIRED[kind]))
                with (staging/f'{kind}.csv').open('w',encoding='utf-8',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(rows)
            manifest={'adapter':VERSION,'coverage':self.coverage,'requests':self.client.records,
                      'csv_sha256':{p.name:digest(p.read_bytes()) for p in sorted(staging.glob('*.csv'))}}
            (staging/'provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
            build(staging,ROOT/'data'/'verified_events.json')  # validate entire batch before promotion
            for p in sorted(staging.iterdir()):
                temp=out/(p.name+'.tmp');temp.write_bytes(p.read_bytes());temp.replace(out/p.name)
        print(json.dumps({k:len(v) for k,v in self.data.items()}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'capture'/'ttscore')
    parser.add_argument('--output',type=Path,default=ROOT/'imports')
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--league',action='append',default=[],help='Known event ID; repeat for multiple leagues')
    parser.add_argument('--ranking',action='append',default=[],help='CATEGORY_ID:latest or CATEGORY_ID:YYYY-MM-DD')
    parser.add_argument('--delay',type=float,default=1)
    args=parser.parse_args()
    importer=Importer(Client(args.cache,args.offline,args.delay))
    importer.catalog()
    print('Catalog:',len(importer.data['events']),flush=True)
    for event in args.league:
        importer.league(event)
        print('League:',event,importer.coverage['leagues'][event],flush=True)
    for ranking in args.ranking:
        category,date=ranking.split(':',1)
        importer.ranking(category,date)
        print('Ranking:',ranking,flush=True)
    importer.export(args.output)

if __name__=='__main__':
    main()
