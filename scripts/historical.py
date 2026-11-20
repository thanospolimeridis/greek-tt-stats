#!/usr/bin/env python3
"""Resumable public group, knockout, consolation and doubles backfill.

Each event is checkpointed privately; exports merge into the verified archive.
No athlete identities are inferred from abbreviated doubles labels.
"""
import argparse
import csv
import datetime as dt
import json
from pathlib import Path
import re
from ttscore import BASE, ROOT, Client, Document, Node, Importer, SourceAccessError, clean, digest, options, schedule_rows
from import_csv import DataError, TYPES, build, parse_games
from compact_brackets import compact_games, bracket_byes


def game_score(cells):
    score=re.fullmatch(r'(\d+)\s*-\s*(\d+)',cells[5])
    if not cells[5].strip():
        return None
    if not score:
        raise DataError('unrecognized_final_score')
    if max(map(int,score.groups()))==0:
        return None
    a,b=map(int,score.groups())
    if max(a,b) not in (3,4) or min(a,b)>=max(a,b):
        raise DataError('unresolved_final_score')
    raw=cells[4].strip()
    if raw=='W.O':
        raise DataError('walkover_excluded_from_played_results')
    if not re.fullmatch(r'\d+-\d+(?:\s+\d+-\d+)*',raw):
        raise DataError('nonstandard_game_scores')
    games=raw.replace(' ', '|').replace('-', ':')
    parsed=parse_games(games,'historical')
    counts=[0,0]
    for ga,gb in parsed:
        if max(counts)==max(a,b):raise DataError('games_after_decision')
        counts[0 if ga>gb else 1]+=1
    if counts!=[a,b]:raise DataError('set_totals_disagree')
    date=dt.datetime.strptime(cells[1].split(' / ')[0],'%y-%m-%d').date().isoformat()
    return {'date':date,'score1':str(a),'score2':str(b),'games':games,'best_of':str(max(a,b)*2-1),'status':'completed'}


def team_double(importer,entry,event,fixture,key,category,round_,players,games,scores,target):
    partners=[]
    for side,field in [('Home','homep_2'),('Away','awayp_2')]:
        if field not in entry:raise DataError('missing_doubles_partner')
        p=entry[field]
        if int(entry['team_games'][side+'_2'] or -1)<=0:raise DataError('missing_doubles_partner')
        partners.append(importer.player(p['AM'],clean(str(p['LastName'] or '')+' '+str(p['FirstName'] or '')),event+'-'+entry['team_games'][side+'_2'],key))
    if len(set(players+partners))!=4:raise DataError('duplicate_doubles_members')
    return {'id':'ttscore-team-game-'+entry['team_games']['ID'],'event_id':'ttscore-'+event,'date':fixture['date'],
            'side1_name':importer.data['players'][players[0]]['name']+' / '+importer.data['players'][partners[0]]['name'],
            'side2_name':importer.data['players'][players[1]]['name']+' / '+importer.data['players'][partners[1]]['name'],
            'player1_id':players[0],'partner1_id':partners[0],'player2_id':players[1],'partner2_id':partners[1],
            'winner_side':'1' if scores[0]>scores[1] else '2','status':'completed','score1':str(scores[0]),'score2':str(scores[1]),
            'games':'|'.join(games),'best_of':str(2*target-1),'fixture_id':fixture['id'],'category':category,'round':round_,
            'source_id':key,'source_url':BASE+'/game-team.php?game='+fixture['id'].removeprefix('ttscore-game-')+'&customer=24',
            'identity_status':'resolved_members'}


def ko_groups(body):
    """Bind each game to its explicit bracket participant IDs when available."""
    groups={}
    for ul in Document(body).find('ul'):
        if 'koround' not in ul.attrs.get('class','').split():continue
        children=[x for x in ul.children if isinstance(x,Node) and x.tag=='li']
        for i,node in enumerate(children):
            if 'data-gameid' not in node.attrs:continue
            if i==0 or i+1==len(children):raise DataError('broken_knockout_structure')
            participants=[]
            for side in (children[i-1],children[i+1]):
                ids=re.findall(r'loadPlayer\(24,\d+,(\d+)', ' '.join(a.attrs.get('onclick','') for a in side.find('a')))
                participants.append(ids[0] if len(ids)==1 else None)
            groups.setdefault(node.attrs['data-groupid'],{})[node.attrs['data-gameid']]=participants
    return groups


def group_players(body):
    """Scope displayed participant labels to their explicit group table."""
    groups={}
    for table in Document(body).find('table'):
        if 'groupTable' not in table.attrs.get('class','').split():continue
        links=list(table.find('button'))+list(table.find('a'))
        ids={m[1] for node in links
             if (m:=re.search(r"loadSchedule\('(\d+)'",node.attrs.get('onclick','')))}
        if len(ids)!=1:raise DataError('ambiguous_group_table')
        mapping={}
        for node in table.find('a'):
            ident=re.search(r'loadPlayer\(24,\d+,(\d+)',node.attrs.get('onclick',''))
            if ident:mapping[ident[1]]=clean(node.text())
        group=next(iter(ids))
        if group in groups and groups[group]!=mapping:raise DataError('conflicting_group_participants')
        groups[group]=mapping
    return groups


class History(Importer):
    def skip_bracket_bye(self,candidate,bindings,participants):
        if not candidate or bindings!={candidate['game']:candidate['participants']}:return False
        if participants.get(candidate['player'],{}).get('team')!=0:return False
        self.counts['explicit_bracket_byes']=self.counts.get('explicit_bracket_byes',0)+1
        return True

    def import_compact(self,event,phase,category,group,candidate,bindings,participants,key,source):
        """Use a fully resolved singles bracket, otherwise retain detail retrieval."""
        if not candidate or bindings!={candidate['game']:candidate['participants']}:return False
        try:
            p1,p2=[participants[i] for i in candidate['participants']]
            if p1['team']!=0 or p2['team']!=0:return False
            result=game_score(candidate['cells'])
            if not result:return False
        except (DataError,KeyError,ValueError,TypeError):return False
        if getattr(self,'result_cutoff',None) and result['date']>self.result_cutoff:
            # Keep the established detail-page evidence for excluded rows.
            return False
        self.put('matches',{'id':'ttscore-game-'+candidate['game'],'event_id':'ttscore-'+event,
            'phase':phase,'category':category,'round':'0','source_url':source,'source_id':key,**result,
            'player1_id':p1['player'],'player2_id':p2['player'],
            'winner_id':p1['player'] if int(result['score1'])>int(result['score2']) else p2['player'],
            'club1_id':p1['club'],'club2_id':p2['club']})
        self.counts['compact_bracket_matches']=self.counts.get('compact_bracket_matches',0)+1
        return True

    def put(self,kind,row):
        if kind in ('matches','doubles','fixtures') and row['id'] in self.data[kind]:
            old=self.data[kind][row['id']]
            keys=('event_id','date','player1_id','player2_id','partner1_id','partner2_id','side1_name','side2_name',
                  'score1','score2','games','status','winner_id','winner_side','best_of','fixture_id',
                  'home_club_id','away_club_id','home_score','away_score')
            if any(old.get(k,'')!=row.get(k,'') for k in keys):raise DataError('conflicting_duplicate_game')
            return
        super().put(kind,row)

    def issue(self,event,phase,reason,**extra):
        self.coverage['issues'].append({'event':event,'phase':phase,'reason':str(reason),**extra})

    def participants(self,event,category):
        body,key=self.client.get('/tournament_players.php',{'event':event,'customer':'24','getStats':'1','agecategoryid_players':category})
        rows=json.loads(body)
        if not isinstance(rows,list):raise DataError('participant_schema_changed')
        result={}
        for p in rows:
            if str(p['EventID'])!=event:raise DataError('participant_event_mismatch')
            ident=str(p['ID'])
            team=int(p['Team'])
            result[ident]={'team':team}
            if team==0:
                result[ident].update(player=self.player(p.get('AM'),clean(str(p['LastName'] or '')+' '+str(p['FirstName'] or '')),event+'-'+ident,key),club=self.club(p.get('clubname')))
        return result

    def import_schedule(self,event,phase,category,group,mapping,participants,bindings=None):
        url=f'/rounds_schedule2.php?group={group}&customer=24'
        body,key=self.client.get(url)
        type_match=re.search(r'refreshScheduleTable\((\d)\)',body)
        if not type_match:raise DataError('missing_schedule_discipline')
        discipline=int(type_match[1])
        if discipline==2:
            summary=self.coverage.setdefault('team_tournaments',{}).setdefault(event,{
                'fixtures_discovered':0,'fixtures_imported':0,'singles_imported':0,'doubles_imported':0,
                'excluded_rows':0,'unused_rows':0,'review_rows':0,'historical_complete':False})
            for game,cells in schedule_rows(body):
                try:self.fixture(event,game,cells,key,BASE+url,category,summary,phase)
                except SourceAccessError:raise
                except (DataError,ValueError,KeyError,TypeError) as exc:
                    summary['review_rows']+=1
                    self.issue(event,phase,exc,game=game,source_id=key)
            return
        rows=schedule_rows(body)
        for game,cells in rows:
            try:
                result=game_score(cells)
                if result is None:
                    self.counts['unplayed_or_bye']+=1;continue
                if getattr(self,'result_cutoff',None) and result['date']>self.result_cutoff:
                    self.issue(event,phase,'result_after_snapshot_cutoff',game=game,
                               date=result['date'],cutoff=self.result_cutoff,source_id=key)
                    continue
                common={'id':'ttscore-game-'+game,'event_id':'ttscore-'+event,'phase':phase,'category':category,'round':cells[0],
                        'source_url':BASE+url,'source_id':key,**result}
                if discipline==1:
                    names=cells[3].split(' - ')
                    if len(names)!=2 or not all(names):raise DataError('ambiguous_pair_labels')
                    self.put('doubles',{**common,'side1_name':names[0],'side2_name':names[1],
                             'winner_side':'1' if int(result['score1'])>int(result['score2']) else '2','identity_status':'source_pair_labels_only'})
                    self.counts['doubles']+=1
                else:
                    ids=(bindings or {}).get(game)
                    if not ids or None in ids:
                        candidates=[(a,b) for a,an in mapping.items() for b,bn in mapping.items() if a!=b and cells[3]==an+' - '+bn]
                        if len(candidates)!=1:raise DataError('ambiguous_or_missing_player_mapping')
                        ids=candidates[0]
                    p1,p2=[participants[i] for i in ids]
                    if p1['team']!=0 or p2['team']!=0:raise DataError('participant_discipline_mismatch')
                    self.put('matches',{**common,'player1_id':p1['player'],'player2_id':p2['player'],
                             'winner_id':p1['player'] if int(result['score1'])>int(result['score2']) else p2['player'],
                             'club1_id':p1['club'],'club2_id':p2['club']})
                    self.counts['singles']+=1
            except (DataError,KeyError,ValueError) as exc:self.issue(event,phase,exc,game=game,source_id=key)

    def phase(self,event,phase,path,field,series=None,category_limit=None):
        selector,key=self.client.get(path)
        cats=options(selector,field)
        selected=cats[:category_limit] if category_limit else cats
        self.counts['categories_discovered']+=len(cats)
        self.counts['categories_selected']+=len(selected)
        for cat,label in selected:
            try:
                self.category(event,phase,path,field,series,cat,label)
                self.counts['categories_visited']=self.counts.get('categories_visited',0)+1
                if getattr(self,'progress',None):self.progress(phase,label)
            except SourceAccessError:raise
            except (DataError,ValueError,KeyError,TypeError) as exc:
                self.issue(event,phase,exc,category=label)

    def category(self,event,phase,path,field,series,cat,label):
        participants=self.participants(event,cat)
        form={'event':event,'customer':'24','getStats':'1',field:cat}
        endpoint=path.split('?')[0]
        if series:form['series']=series
        body,key=self.client.get(endpoint,form)
        visited=set()
        while True:
            mapping={}
            for a in Document(body).find('a'):
                ident=re.search(r'loadPlayer\(24,\d+,(\d+)',a.attrs.get('onclick',''))
                if ident:mapping[ident[1]]=clean(a.text())
            groups=ko_groups(body) if series else {g:None for g in re.findall(r"loadSchedule\('(\d+)'",body)}
            compact=compact_games(body) if series and getattr(self,'compact_brackets',False) else {}
            byes=bracket_byes(body) if series and getattr(self,'skip_bracket_byes',False) else {}
            scoped_players={} if series else group_players(body)
            if not groups and body.strip():
                self.issue(event,phase,'no_groups_in_response',category=label,source_id=key)
            for group,bindings in groups.items():
                if self.skip_bracket_bye(byes.get(group),bindings,participants):
                    pass
                elif not self.import_compact(event,phase,label,group,compact.get(group),bindings,participants,key,BASE+path):
                    self.import_schedule(event,phase,label,group,mapping if series else scoped_players.get(group,{}),participants,bindings)
                self.counts['groups_visited']+=1
            links=re.findall(r"nextPage\('([^']+)'",body)
            if not links:break
            if len(set(links))!=1:raise DataError('ambiguous_pagination')
            nexturl=links[0]
            if not re.fullmatch(re.escape(BASE)+r'/rounds_schedule2\.php\?tournament=\d+&customer=24&page=\d+',nexturl) or nexturl in visited:
                raise DataError('invalid_or_cyclic_pagination')
            visited.add(nexturl)
            body,key=self.client.get(nexturl[len(BASE):])

    def event(self,event,category_limit=None,as_of=None,available_results=False):
        record=self.data['events']['ttscore-'+event]
        cutoff=as_of or dt.date.today().isoformat()
        unfinished=not record.get('end_date') or record['end_date']>=cutoff
        if unfinished and (not available_results or record.get('start_date','')>cutoff):
            raise DataError('Event is ongoing, future-dated, or undated; review dated available results explicitly')
        self.result_cutoff=cutoff if unfinished else None
        body,key=self.client.get('/customer/24/event/'+event)
        self.counts={'singles':0,'doubles':0,'unplayed_or_bye':0,'groups_visited':0,'categories_discovered':0,'categories_selected':0,'categories_visited':0}
        phases=[]
        # Only follow the actual navigation, including parameter ordering supplied by the source.
        links=re.findall(r"loadQueryResults\('https://app.ttscore.io/([^']+)'",body)
        for link in dict.fromkeys(links):
            if link.startswith('tournament_groups_league.php?'):phases.append(('league','/'+link,'agecategoryid_league',None))
            if link.startswith('rounds_schedule2.php?'):phases.append(('groups','/'+link,'agecategoryid_groups',None))
            if link.startswith('tournament_ko_games.php?'):
                series=re.search(r'series=(\d+)',link)[1]
                phases.append(('knockout' if series=='1' else 'consolation','/'+link,'agecategoryid_ko',series))
        start=len(self.coverage['issues'])
        for phase,path,field,series in phases:
            try:
                if phase=='league':self.league(event)
                else:self.phase(event,phase,path,field,series,category_limit)
            except SourceAccessError:raise
            except (DataError,ValueError,KeyError) as exc:self.issue(event,phase,exc)
        if not phases:self.issue(event,'navigation','no_supported_individual_views')
        self.counts['singles']=len(self.data['matches'])
        self.counts['doubles']=len(self.data['doubles'])
        self.counts['fixtures']=len(self.data['fixtures'])
        self.coverage.setdefault('events',{})[event]={**self.counts,'phases':[p[0] for p in phases],
                    'issues':len(self.coverage['issues'])-start,'status':'partial' if len(self.coverage['issues'])>start or category_limit else 'public_views_traversed',
                    'historical_complete':False}
        if getattr(self,'compact_brackets',False):
            self.coverage['events'][event]['retrieval_mode']=(
                'compact_brackets_v2' if getattr(self,'skip_bracket_byes',False) else 'compact_brackets_v1')
        if unfinished:
            self.coverage['events'][event].update(scope='available_results',snapshot_date=cutoff,
                date_status='undated' if not record.get('end_date') else 'ongoing',status='partial')
        return self.coverage['events'][event]


def restore_base(importer,path):
    build(path,ROOT/'data'/'verified_events.json')
    for kind in TYPES:
        p=path/f'{kind}.csv'
        if p.exists():
            with p.open(encoding='utf-8') as source:
                for row in csv.DictReader(source):importer.data[kind][row['id']]={k:v for k,v in row.items() if v!=''}
    provenance=json.loads((path/'provenance.json').read_text())
    importer.client.records.update(provenance['requests'])
    importer.coverage=provenance['coverage']


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--event',action='append',default=[])
    ap.add_argument('--balanced',action='store_true',help='Use the reviewed cross-season backfill plan')
    ap.add_argument('--all-events',action='store_true')
    ap.add_argument('--category-limit',type=int)
    ap.add_argument('--offline',action='store_true')
    ap.add_argument('--output',type=Path,default=ROOT/'imports')
    ap.add_argument('--cache',type=Path,default=ROOT/'capture'/'ttscore')
    ap.add_argument('--checkpoint',type=Path,default=ROOT/'capture'/'history-checkpoints')
    args=ap.parse_args()
    if args.category_limit is not None and args.category_limit < 1:
        ap.error('--category-limit must be positive')
    if not (args.event or args.balanced or args.all_events):
        ap.error('select --event, --balanced, or --all-events')
    client=Client(args.cache,args.offline)
    base=History(client);restore_base(base,ROOT/'imports')
    selected=list(args.event)
    if args.balanced:
        plan=json.loads((ROOT/'data'/'backfill-plan.json').read_text())
        for item in plan['events']:
            if base.data['events']['ttscore-'+item['event']]['season']!=item['season']:
                raise DataError('Backfill plan season disagrees with source catalog')
            selected.append(item['event'])
    if args.all_events:selected += [e.removeprefix('ttscore-') for e in base.data['events']]
    selected=sorted(set(selected),key=int)
    args.checkpoint.mkdir(parents=True,exist_ok=True)
    adapter_hash=digest(b''.join(Path(__file__).with_name(name).read_bytes()
                               for name in ('historical.py','ttscore.py','import_csv.py')))
    for event in dict.fromkeys(selected):
        if 'ttscore-'+event not in base.data['events']:raise DataError('Unknown event')
        checkpoint=args.checkpoint/f'{event}-{args.category_limit or "all"}-{adapter_hash[:12]}.json'
        if checkpoint.exists() and not args.offline:
            saved=json.loads(checkpoint.read_text())
        else:
            imp=History(client);imp.data['events']=base.data['events'].copy()
            try:
                summary=imp.event(event,args.category_limit)
            except SourceAccessError:raise
            except DataError as exc:
                imp.coverage.setdefault('events',{})[event]={'singles':0,'doubles':0,'phases':[],'categories_selected':0,'categories_discovered':0,'issues':1,'status':'not_processed','historical_complete':False}
                imp.issue(event,'event',exc)
            saved={'data':imp.data,'coverage':imp.coverage,'requests':client.records}
            # Checkpoint only after normalization; export validates all tables again.
            checkpoint.write_text(json.dumps(saved,ensure_ascii=False)+'\n')
        for kind,rows in saved['data'].items():
            if kind=='events':continue
            for ident,row in rows.items():
                if kind in ('players','clubs') and ident in base.data[kind]:
                    if kind=='players':
                        old=base.data[kind][ident]
                        aliases=set(filter(None,old.get('aliases','').split('|')))|set(filter(None,row.get('aliases','').split('|')))
                        if row['name']!=old['name']:aliases.add(row['name'])
                        old['aliases']='|'.join(sorted(aliases-{old['name']}))
                    continue
                base.put(kind,row)
        client.records.update(saved['requests'])
        base.coverage.setdefault('events',{}).update(saved['coverage'].get('events',{}))
        # Replace event issues on replay, keeping existing league review evidence.
        base.coverage['issues']=[i for i in base.coverage['issues'] if not (i.get('event')==event and i.get('phase'))]
        base.coverage['issues']+=saved['coverage']['issues']
        print(event,base.coverage['events'][event],flush=True)
    base.coverage['backfill_plan']={'events':list(dict.fromkeys(selected)),'scope':'selected_tournaments_across_seasons','historical_complete':False,'plan_sha256':digest((ROOT/'data'/'backfill-plan.json').read_bytes()),'adapter_sha256':adapter_hash}
    # Reprocess existing league to include its four known doubles, preserving singles.
    league=History(client);league.data['events']=base.data['events'].copy();league.league('777')
    for kind in ('players','clubs','doubles'):
        for ident,row in league.data[kind].items():
            if ident not in base.data[kind]:base.put(kind,row)
    base.coverage['leagues']['777']=league.coverage['leagues']['777']
    base.coverage['issues']=[i for i in base.coverage['issues'] if not (i.get('event')=='777' and not i.get('phase'))]+league.coverage['issues']
    base.export(args.output)

if __name__=='__main__':main()
