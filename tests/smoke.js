'use strict';
const fs=require('fs');
const path=require('path');
const vm=require('vm');
const assert=require('assert');
const root=path.join(__dirname,'..');
const script=fs.readFileSync(path.join(root,'src','app.js'),'utf8');
const published=JSON.parse(fs.readFileSync(path.join(root,'data','catalog.json'),'utf8'));
const db={events:JSON.parse(fs.readFileSync(path.join(root,'data','verified_events.json'),'utf8')),players:[],clubs:[],matches:[],fixtures:[],rankings:[],meta:{data_coverage:'event_catalog_only'}};
let checks=0;
function check(value,message){assert(value,message);checks++}
function render(route,data=db,lang='el',fetcher,extras={}){
  const container={innerHTML:''};
  const handlers={};
  const context={
    document:{documentElement:{lang:'el'},getElementById(id){return id==='site-data'?{textContent:JSON.stringify(data)}:id==='app'?container:null},addEventListener(name,fn){handlers[name]=fn}},
    window:{addEventListener(name,fn){handlers[name]=fn},scrollTo(){}},
    localStorage:{getItem(){return lang},setItem(){}},
    location:{hash:'#'+route},Intl,URL,encodeURIComponent,decodeURIComponent,console,fetch:fetcher,...extras
  };
  vm.runInNewContext(script,context,{timeout:5000});
  return {get html(){return container.innerHTML},handlers,context,
    change(id,value){handlers.change({target:{id,value}})},
    click(id){handlers.click({target:{closest(sel){return sel==='#'+id?{}:null}}})},
    search(value){handlers.input({target:{id:'search-roster',value,matches(){return true}}})}};
}
for(const route of ['home','events','players','clubs','rankings','h2h','about','event/ttscore-777']){
  check(render(route,published).html.includes('</main>'),'Published data route '+route);
}
check(render('players').html.includes('Δεν έχουν εισαχθεί'),'Honest empty player state');
check(render('%broken').html.includes('404'),'Malformed hash does not crash');
check(render('player/missing').html.includes('404'),'Unknown player');
const sample=structuredClone(db);
sample.clubs=[{id:'c1',name:'Test Club'},{id:'c2',name:'Other Club'}];
sample.players=[{id:'p1',name:'Γιώργος Παίκτης',club_id:'c1',aliases:'George Player'},{id:'p2',name:'Player Two',club_id:'c2'}];
sample.matches=[
 {id:'m1',event_id:'ttscore-777',date:'2026-02-03',player1_id:'p1',player2_id:'p2',winner_id:'p1',score1:3,score2:1,games:[[11,5],[5,11],[11,8],[11,7]],status:'completed',source_url:'https://app.ttscore.io/test'},
 {id:'m2',event_id:'ttscore-777',date:'2026-02-04',player1_id:'p1',player2_id:'p2',winner_id:'p2',score1:0,score2:3,status:'walkover',source_url:'https://app.ttscore.io/test'}];
sample.rankings=[
 {id:'r1',player_id:'p1',category:'Men',date:'2026-02-03',rank:15,points:99,source_url:'https://app.ttscore.io/test'},
 {id:'r2',player_id:'p1',category:'Men',date:'2026-01-03',rank:20,points:88,source_url:'https://app.ttscore.io/test'}];
sample.fixtures=[{id:'f1',event_id:'ttscore-777',home_club_id:'c1',away_club_id:'c2',status:'completed',date:'2026-02-03',home_score:4,away_score:1,source_url:'https://app.ttscore.io/test'}];
check(render('player/p1',sample).html.includes('100%'),'Walkover excluded from win rate');
const rankingsOnly=structuredClone(sample);rankingsOnly.matches=[];
const missingHistory=render('player/p1',rankingsOnly,'en').html;
check(missingHistory.includes('No completed singles results have been imported for this player yet.')&&missingHistory.includes('#15'),'Ranking-only profile explicitly distinguishes missing match history');
check(!missingHistory.includes('<strong>0</strong>')&&(missingHistory.match(/<strong>—<\/strong>/g)||[]).length===3,'Missing history does not imply zero career wins or losses');
check(render('player/p1',rankingsOnly,'el').html.includes('Αυτό δεν σημαίνει ότι δεν έχει αγωνιστεί'),'Greek profile explains missing results');
const second=render('player/p2',sample,'en');
check(second.html.includes('✕ 1–3'),'Score oriented to profile player');
check(second.html.includes('5–11, 11–5, 8–11, 7–11'),'Game scores oriented to player');
check(second.html.includes('Walkover'),'Non-completed result visible in history');
const h2h=render('h2h',sample,'en');h2h.change('h2h-player1','p2');h2h.change('h2h-player2','p1');
check(h2h.html.includes('Player Two · 0'),'H2H excludes walkover');
check(h2h.html.includes('✕ 1–3'),'H2H score orientation');
h2h.change('h2h-player2','p2');check(h2h.html.includes('two distinct'),'Self-comparison prevented');
const rankings=render('rankings',sample,'en');
check(rankings.html.includes('#15')&&!rankings.html.includes('#20'),'Latest snapshot default');
rankings.change('ranking-date','2026-01-03');check(rankings.html.includes('#20')&&!rankings.html.includes('#15'),'Historical snapshot selection');
const search=render('players',sample);
for(const query of ['γιωργος','giorgos','George']){search.search(query);check(search.html.includes('Γιώργος Παίκτης')&&!search.html.includes('Player Two'),'Greek/Latin/alias search: '+query)}
const switcher=render('home');switcher.click('lang-switch');
check(switcher.context.document.documentElement.lang==='en','HTML language switched');
check(switcher.html.includes('Competitions'),'Actual rerender in English');
check(render('club/c1',sample,'en').html.includes('Team fixture statistics'),'Club statistics rendered');
const unsafe=structuredClone(sample);unsafe.players[0].name='<img src=x onerror=alert(1)>';
check(!render('player/p1',unsafe).html.includes('<img src=x'),'Names are HTML escaped');
const many=structuredClone(db);many.players=Array.from({length:60},(_,i)=>({id:'p'+i,name:'Player '+String(i).padStart(2,'0')}));
const paging=render('players',many,'en');
check(paging.html.includes('Player 49')&&!paging.html.includes('Player 50'),'Player pagination first page');
paging.click('page-next');check(paging.html.includes('Player 59')&&!paging.html.includes('Player 00'),'Player pagination second page');
paging.search('Player 00');check(paging.html.includes('Player 00'),'Search resets pagination');
const pairSample=structuredClone(sample);
pairSample.doubles=[{id:'d1',event_id:'ttscore-777',date:'2026-02-03',side1_name:'A / B',side2_name:'C / D',winner_side:'1',score1:3,score2:0,games:[[11,5],[11,5],[11,5]],status:'completed',identity_status:'source_pair_labels_only',source_url:'https://app.ttscore.io/test'}];
const doublesView=render('event/ttscore-777',pairSample,'en');
check(doublesView.html.includes('id="tab-doubles"')&&!doublesView.html.includes('A / B'),'Doubles have their own event tab');
doublesView.click('tab-doubles');
check(doublesView.html.includes('A / B'),'Doubles results visible on tournament');
check(doublesView.html.includes('individual identities unresolved'),'Unresolved pair identities disclosed');
check(render('player/p1',pairSample,'en').html.includes('100%'),'Doubles do not affect singles statistics');
check(!render('player/p1',pairSample,'en').html.includes('A / B'),'Unresolved pair labels do not create profile history');
pairSample.doubles[0]={...pairSample.doubles[0],player1_id:'p1',partner1_id:'p3',player2_id:'p2',partner2_id:'p4',identity_status:'resolved_members'};
check(render('player/p1',pairSample,'en').html.includes('A / B'),'Resolved doubles appear in member history');
const phasesSample=structuredClone(sample);phasesSample.matches[0].phase='groups';
const phaseView=render('event/ttscore-777',phasesSample,'en');
check(phaseView.html.includes('id="tab-players"')&&phaseView.html.includes('Γιώργος Παίκτης'),'Event opens on the per-player summary');
phaseView.click('tab-matches');
check(phaseView.html.includes('3–1'),'Group result visible before filtering');
phaseView.change('phase-filter','knockout');
check(!phaseView.html.includes('3–1'),'Phase filter excludes group matches');


const longHistory=structuredClone(sample);
longHistory.matches=Array.from({length:51},(_,i)=>({...sample.matches[0],id:'history-'+i,source_url:'https://app.ttscore.io/history-'+i}));
const historyPage=render('player/p1',longHistory,'en');
check(historyPage.html.includes('history-49')&&!historyPage.html.includes('history-50'),'Long player histories paginate');
check(historyPage.html.includes('<strong>51</strong>'),'Player totals include all pages');
historyPage.click('page-next');check(historyPage.html.includes('history-50')&&!historyPage.html.includes('history-49'),'Older player results remain accessible');
const coverageSample=structuredClone(sample);
coverageSample.events.push({id:'ttscore-9999',name:'Deferred Competition',season:'2026-27',source_url:'https://app.ttscore.io/customer/24/event/9999'});
coverageSample.meta.provenance={coverage:{event_catalog:{count:coverageSample.events.length,seasons:['2025-26','2026-27']},events:{777:{singles:1,doubles:0,issues:2,phases:['league']}},leagues:{},rankings:[],batch:{attempted:1,eligible:2,pending:1,as_of:'2026-11-20',deferred:[{event:'9999',reason:'not_finished_by_cutoff'}]}}};
const coveragePage=render('about',coverageSample,'en');
check(coveragePage.html.includes('1/2 additional competitions checked'),'Batch progress is explicit');
check(coveragePage.html.includes('Not finished by the reference date'),'Deferred competitions are distinguished from imported events');
check(coveragePage.html.includes('does not establish complete history'),'Traversal is not labelled historical completeness');
check(render('event/ttscore-9999',coverageSample,'en').html.includes('Not finished by the reference date'),'Event page explains deferral');
coverageSample.meta.provenance.coverage.events['777'].scope='available_results';
coverageSample.meta.provenance.coverage.events['777'].snapshot_date='2026-11-20';
check(render('event/ttscore-777',coverageSample,'en').html.includes('Partial results through'),'Ongoing results disclose the dated partial snapshot');
const kinds=structuredClone(sample);
kinds.events=[{id:'ttscore-1',name:'Open A',season:'2025-26'},{id:'ttscore-2',name:'League B',season:'2025-26'},{id:'ttscore-3',name:'Cup C',season:'2025-26'},{id:'ttscore-4',name:'Queued D',season:'2025-26'}];
kinds.matches=[];
kinds.meta={event_match_counts:{'ttscore-1':5,'ttscore-2':3,'ttscore-3':2},provenance:{coverage:{events:{1:{phases:['groups','knockout']},2:{phases:['league']},3:{phases:['knockout']}},leagues:{},team_tournaments:{3:{}}}}};
const kindList=render('events',kinds,'en');
check(kindList.html.includes('Individual tournament')&&kindList.html.includes('Team · league table')&&kindList.html.includes('Team · knockout'),'Tournaments and leagues share one list with type labels');
check(!kindList.html.includes('Queued D'),'Competitions without results are hidden by default');
kindList.handlers.change({target:{id:'results-only',checked:false}});
check(kindList.html.includes('Queued D')&&kindList.html.includes('Not yet checked'),'Unchecked competitions stay visible on request and are not guessed');
check(render('event/ttscore-3',kinds,'en').html.includes('Team · knockout'),'Team cups with knockout views are not labelled individual');
const scoped=structuredClone(sample);scoped.events.push({id:'ttscore-5',name:'Solo Open',season:'2025-26'});
scoped.meta.provenance={coverage:{events:{5:{phases:['groups']},777:{phases:['league']}},leagues:{}}};
scoped.matches.push({...sample.matches[0],id:'m3',event_id:'ttscore-5',winner_id:'p2',score1:1,score2:3});
const profile=render('player/p1',scoped,'en');
check(profile.html.includes('All competitions · 2')&&profile.html.includes('Individual tournaments · 1')&&profile.html.includes('Team competitions · 1'),'Profile splits the same history by type');
profile.click('scope-individual');
check(profile.html.includes('✕ 1–3')&&!profile.html.includes('✓ 3–1'),'Type filter narrows the profile history');
const charted=structuredClone(sample);
charted.rankings.push({id:'r0',player_id:'p1',category:'Men',date:'2025-01-03',rank:31,points:70,source_url:'https://app.ttscore.io/test'});
const chart=render('player/p1',charted,'en');
const points=()=>(chart.html.match(/class="pt"/g)||[]).length;
check(chart.html.includes('Ranking points over time')&&points()===2,'Ranking chart opens on one year of official snapshots');
chart.click('range-all');check(points()===3&&chart.html.includes('3/3 snapshots in range'),'All range plots every snapshot');
chart.click('range-3m');check(points()===2,'Range is measured back from the latest snapshot');
check(!chart.html.includes('rating'),'Official ranking points are never called a rating');
const unscored=structuredClone(sample);for(const r of unscored.rankings)r.points=null;
check(render('player/p1',unscored,'en').html.includes('Ranking position over time'),'Snapshots without points fall back to ranking position');
const youth=structuredClone(sample);
youth.rankings=[
 {id:'y1',player_id:'p1',category:'Παίδες',date:'2026-01-03',rank:4,points:900,source_url:'https://app.ttscore.io/test'},
 {id:'y2',player_id:'p1',category:'Έφηβοι',date:'2026-02-03',rank:2,points:950,source_url:'https://app.ttscore.io/test'},
 {id:'y3',player_id:'p1',category:'Άνδρες',date:'2026-02-03',rank:120,points:950,source_url:'https://app.ttscore.io/test'}];
const career=render('player/p1',youth,'en').html;
check((career.match(/class="pt"/g)||[]).length===2&&!career.includes('id="chart-category"'),'Age categories share one points line per date');
check(career.includes('<br>#120 · Άνδρες<br>#2 · Έφηβοι')&&career.includes('#120 Άνδρες · #2 Έφηβοι'),'Every category position is shown, senior category first');
youth.rankings[2].points=990;
check(render('player/p1',youth,'en').html.includes('id="chart-category"'),'Diverging points fall back to one category at a time');
const rankSearchData=structuredClone(sample);
rankSearchData.players.push({id:'httf-24084',name:'Third Player'});
rankSearchData.rankings.push({id:'r3',player_id:'p2',category:'Men',date:'2026-02-03',rank:3,points:120,source_url:'https://app.ttscore.io/test'},
 {id:'r4',player_id:'httf-24084',category:'Men',date:'2026-02-03',rank:40,points:50,source_url:'https://app.ttscore.io/test'});
const rankSearch=render('rankings',rankSearchData,'en');
const typeRanking=value=>rankSearch.handlers.input({target:{id:'search-rankings',value,matches(){return true}}});
check(rankSearch.html.includes('id="search-rankings"')&&rankSearch.html.includes('Player Two')&&rankSearch.html.includes('Third Player'),'Rankings page offers an athlete search');
typeRanking('giorgos');
check(rankSearch.html.includes('Γιώργος Παίκτης')&&!rankSearch.html.includes('Player Two')&&rankSearch.html.includes('#15')&&rankSearch.html.includes('1 ranking entries match'),'Rankings search finds an athlete by transliterated name and keeps the real position');
rankSearch.change('ranking-date','2026-01-03');
check(rankSearch.html.includes('#20')&&!rankSearch.html.includes('#15'),'Search follows the athlete to a past snapshot');
rankSearch.change('ranking-date','latest');typeRanking('24084');
check(rankSearch.html.includes('Third Player')&&rankSearch.html.includes('#40')&&!rankSearch.html.includes('Γιώργος Παίκτης'),'Rankings search accepts a registration number');
typeRanking('nobody here');
check(rankSearch.html.includes('There are no records matching this selection.'),'Empty search explains there is no match, not missing data');
const row=(group,slot,points,club,extra={})=>({id:`ttscore-standing-${group}-${slot}`,event_id:'ttscore-777',group_id:group,category:'Men',slot,club_name:club,team_name:club,club_id:'',wins:1,losses:0,disqualified:0,points,as_of:'2026-11-20',source_id:'s',source_url:'https://app.ttscore.io/tournament_groups_league.php?event=777&customer=24',...extra});
const league=structuredClone(sample);
league.standings=[row('55',1,4,'Slot One'),row('55',2,9,'Test Club',{club_id:'c1',disqualified:3}),row('55',3,4,'Slot Three',{team_name:'Slot Three B'}),row('55',4,2,'A.C. Dotted',{team_name:'AC Dott'}),
 row('56',1,0,'Unplayed One',{category:'Women',wins:0}),row('56',2,0,'<b>Unplayed</b>',{category:'Women',wins:0})];
const table=render('event/ttscore-777',league,'en');
const cells=html=>[...html.matchAll(/<tr><td><strong>([^<]*)<\/strong><\/td><td>(?:<a[^>]*>)?([^<]*)/g)].map(m=>m[1]+' '+m[2]);
check(table.html.includes('id="tab-standings"')&&table.html.includes('aria-selected="true">Standings'),'League pages open on the standings tab');
check(JSON.stringify(cells(table.html).slice(0,4))===JSON.stringify(['1 Test Club','2= Slot One','2= Slot Three','4 A.C. Dotted']),'Teams are ordered by the source points and level teams share a position');
check(table.html.includes('href="#club/c1"')&&table.html.includes('<td>3</td><td><strong>9</strong>'),'Standings link known clubs and show the published Disq and points');
check(table.html.includes('<div class="smalltext">Slot Three B</div>')&&!table.html.includes('AC Dott'),'A second team label is shown only when it adds to the club name');
check(JSON.stringify(cells(table.html).slice(4))===JSON.stringify(['— Unplayed One','— &lt;b&gt;Unplayed&lt;/b&gt;'])&&table.html.includes('The source had published no results for this group.'),'A group without published results has no positions');
check(table.html.includes('not calculated from the fixtures in this archive')&&table.html.includes('Retrieved from TTScore: 20 Nov 2026'),'Standings are labelled as the source table with its retrieval date');
table.click('tab-players');check(table.html.includes('Γιώργος Παίκτης')&&!table.html.includes('Slot One'),'The other event tabs stay reachable');
check(render('event/ttscore-777',league,'el').html.includes('>Βαθμολογία <span'),'Greek standings tab label');
check(!render('event/ttscore-777',sample,'en').html.includes('tab-standings'),'Events without a published table have no standings tab');
const insight=structuredClone(sample);
insight.players.push({id:'p3',name:'Third Opponent'},{id:'p4',name:'<i>Fourth</i>'});
const single=(id,opp,won,mine,theirs,extra={})=>({id,event_id:'ttscore-777',date:'2026-03-01',player1_id:'p1',player2_id:opp,winner_id:won?'p1':opp,score1:mine,score2:theirs,status:'completed',source_url:'https://app.ttscore.io/test',...extra});
insight.matches=[single('a','p2',true,3,0),single('b','p2',true,3,2),single('c','p2',false,2,3),single('d','p3',false,0,3),single('e','p3',true,3,1),
 {...single('f','p4',true,1,3),player1_id:'p4',player2_id:'p1'},single('g','p4',true,4,3,{best_of:7}),single('h','p2',true,3,0,{status:'walkover'})];
insight.match_ranks={format:'match-ranks-v1',dates:['2026-02-01'],categories:['Men'],rows:{a:[0,0,10,4],b:[0,0,10,20],c:[0,0,10,4],d:[0,0,10,10],e:[0,0,null,7],f:[0,0,2,10]}};
const breakdown=render('player/p1',insight,'en').html;
const stat=(label,record)=>breakdown.includes(`${label}</span><span><b>${record}</b>`);
check(JSON.stringify([...breakdown.matchAll(/class="(?:won|lost)">. (\d+–\d+)<\/span><\/span><b>(\d+)<\/b>/g)].map(m=>m[1]+' x'+m[2]))===JSON.stringify(['3–0 x1','3–1 x2','3–2 x1','4–3 x1','2–3 x1','0–3 x1']),'Score lines count completed singles from the profile player\'s side, wins first');
check(stat('Matches that went to the final game','2–1')&&breakdown.includes('Games won–lost</span><b>18–13</b>'),'Final-game record respects each match format; walkovers are left out');
check(stat('Opponent ranked higher','2–1')&&stat('Opponent ranked lower','1–0')&&stat('Opponent in the same position','0–1')&&stat('No comparison','2–0'),'Record is split by the opponent\'s official position on the match day');
check(JSON.stringify([...breakdown.matchAll(/<strong>#(\d+)<\/strong>/g)].map(m=>m[1]))===JSON.stringify(['2','4','7','20']),'Best wins list the highest-placed beaten opponents first');
check(breakdown.includes('&lt;i&gt;Fourth&lt;/i&gt;')&&!breakdown.includes('<i>Fourth'),'Opponent names in the breakdown are HTML escaped');
check(/Most-played opponents<\/h3>.*?Player Two.*?Fourth.*?Third Opponent.*?3 opponents/s.test(breakdown),'Most-played opponents are ordered by matches, then wins');
check(!breakdown.includes('rating'),'The breakdown never calls official positions a rating');
const unranked=structuredClone(insight);delete unranked.match_ranks;
const plain=render('player/p1',unranked,'en').html;
check(plain.includes('Score lines')&&!plain.includes('Best wins')&&!plain.includes('Opponent ranked higher'),'Ranking panels appear only when positions are known for the player\'s matches');
const noLevel=structuredClone(insight);delete noLevel.match_ranks.rows.d;
check(!render('player/p1',noLevel,'en').html.includes('Opponent in the same position'),'The same-position row is shown only when it happened');
check(!render('player/p1',rankingsOnly,'en').html.includes('Match breakdown'),'Profiles without imported matches show no breakdown');
const scopedBreakdown=render('player/p1',scoped,'en');
check(scopedBreakdown.html.includes('Games won–lost</span><b>4–4</b>'),'Breakdown covers every competition type by default');
scopedBreakdown.click('scope-individual');
check(scopedBreakdown.html.includes('Games won–lost</span><b>1–3</b>'),'Breakdown follows the competition type filter');
check(render('player/p1',insight,'el').html.includes('Ανάλυση αγώνων'),'Greek breakdown heading');
async function hostedChecks(){
 const hosted=structuredClone(sample);
 hosted.meta={...hosted.meta,verified_results:123,table_counts:{doubles:4},event_match_counts:{'ttscore-777':1},
  partitions:{player:{p1:'records/p1.json',p2:'records/p2.json'},event:{'ttscore-777':'records/e1.json'},club:{c1:'records/c1.json'}}};
 hosted.matches=[];hosted.doubles=[];hosted.fixtures=[];
 const payload={matches:sample.matches,doubles:[],fixtures:sample.fixtures};
 const flush=()=>new Promise(resolve=>setImmediate(resolve));
 check(render('home',hosted,'en').html.includes('>123</div>'),'Hosted home retains whole-archive totals without fetching results');
 const pending=[];
 const view=render('player/p1',hosted,'en',url=>new Promise(resolve=>pending.push({url,resolve})));
 check(view.html.includes('Loading results')&&!view.html.includes('No imported'),'Loading is distinct from an empty history');
 view.context.location.hash='#player/p2';view.handlers.hashchange();
 pending[0].resolve({ok:true,json:async()=>payload});await flush();
 check(view.html.includes('Loading results'),'Stale player request cannot replace the current route');
 pending[1].resolve({ok:true,json:async()=>payload});await flush();
 check(view.html.includes('Player Two')&&view.html.includes('✕ 1–3'),'Hosted profile loads the complete player history with oriented scores');
 view.context.location.hash='#home';view.handlers.hashchange();
 check(view.html.includes('>123</div>'),'Navigation preserves global counts after loading a subset');
 view.context.location.hash='#player/p2';view.handlers.hashchange();
 check(pending.length===2&&!view.html.includes('Loading results'),'Revisiting a loaded profile uses its cached result file');
 const failed=render('event/ttscore-777',hosted,'en',async()=>({ok:false}));await flush();
 check(failed.html.includes('Results could not be loaded')&&!failed.html.includes('No imported'),'Failed downloads cannot masquerade as missing historical results');
 const compare=render('h2h',hosted,'en',async()=>({ok:true,json:async()=>payload}));
 compare.change('h2h-player1','p2');compare.change('h2h-player2','p1');await flush();
 check(compare.html.includes('Player Two · 0')&&compare.html.includes('✕ 1–3'),'Hosted H2H uses complete first-player history and excludes walkovers');
 const hostedLeague=render('event/ttscore-777',hosted,'en',async()=>({ok:true,json:async()=>({...payload,standings:league.standings})}));await flush();
 check(hostedLeague.html.includes('Slot One')&&hostedLeague.html.includes('id="tab-standings"'),'Hosted league pages read standings from the event file');
 hostedLeague.context.location.hash='#player/p1';hostedLeague.handlers.hashchange();await flush();
 hostedLeague.context.location.hash='#event/ttscore-777';hostedLeague.handlers.hashchange();
 check(hostedLeague.html.includes('id="tab-standings"'),'Standings survive leaving and reopening the event');
 const hostedInsight=structuredClone(insight);hostedInsight.matches=[];delete hostedInsight.match_ranks;
 hostedInsight.meta={...hostedInsight.meta,partitions:{player:{p1:'records/p1i.json'},event:{},club:{}}};
 const hostedBreakdown=render('player/p1',hostedInsight,'en',async()=>({ok:true,json:async()=>({matches:insight.matches,doubles:[],fixtures:[],match_ranks:insight.match_ranks})}));await flush();
 check(hostedBreakdown.html.includes('Best wins')&&hostedBreakdown.html.includes('<strong>#2</strong>'),'Hosted profiles read match positions from the player file');
 hosted.meta.release_id='old-release';let interval=0;
 const updated=render('home',hosted,'en',async url=>({ok:true,json:async()=>({release_id:'new-release'})}),
  {setInterval(fn,delay){interval=delay;}});
 await flush();
 check(interval===300000&&updated.html.includes('An updated archive is available.')&&updated.html.includes('Load update'),'Hosted pages announce later releases without automatic navigation');
 const rankHosted=structuredClone(sample);
 rankHosted.rankings=[sample.rankings[0]];rankHosted.matches=[];rankHosted.fixtures=[];
 rankHosted.meta={...rankHosted.meta,ranking_dates:{Men:['2026-02-03','2026-01-03']},table_counts:{rankings:2},
  partitions:{player:{p1:'records/p1r.json'},ranking:{'2026-01-03':'records/r0103.json'},event:{},club:{}}};
 const rankFiles={'records/p1r.json':{matches:sample.matches,doubles:[],fixtures:[],rankings:sample.rankings},
  'records/r0103.json':{matches:[],doubles:[],fixtures:[],rankings:[sample.rankings[1]]}};
 const fetchRankFile=async url=>({ok:true,json:async()=>rankFiles[url]});
 const hostedProfile=render('player/p1',rankHosted,'en',fetchRankFile);await flush();
 check((hostedProfile.html.match(/class="pt"/g)||[]).length===2,'Hosted profile charts the full history from the player file');
 const hostedRanks=render('rankings',rankHosted,'en',fetchRankFile);
 check(hostedRanks.html.includes('#15')&&!hostedRanks.html.includes('#20')&&hostedRanks.html.includes('value="2026-01-03"'),'Hosted rankings list every date but inline only the latest snapshot');
 hostedRanks.change('ranking-date','2026-01-03');await flush();
 check(hostedRanks.html.includes('#20')&&!hostedRanks.html.includes('#15'),'A past ranking date loads its own snapshot file');
 const pack=rows=>({format:'ranking-snapshots-v1',snapshots:[...new Map(rows.map(r=>[r.date+'|'+r.category,[r.date,r.category,'s',r.source_url]])).values()],clubs:[''],
  rows:rows.map(r=>[[...new Map(rows.map(x=>[x.date+'|'+x.category,0])).keys()].indexOf(r.date+'|'+r.category),r.player_id,r.rank,r.points,0])});
 const packedHosted=structuredClone(rankHosted);packedHosted.rankings=pack([sample.rankings[0]]);
 const packedFiles={'records/p1r.json':{matches:sample.matches,doubles:[],fixtures:[],rankings:pack(sample.rankings)},
  'records/r0103.json':{matches:[],doubles:[],fixtures:[],rankings:pack([sample.rankings[1]])}};
 const fetchPacked=async url=>({ok:true,json:async()=>packedFiles[url]});
 const packedProfile=render('player/p1',packedHosted,'en',fetchPacked);await flush();
 check((packedProfile.html.match(/class="pt"/g)||[]).length===2&&packedProfile.html.includes('#15 Men'),'Compact ranking files decode into the profile chart');
 const packedRanks=render('rankings',packedHosted,'en',fetchPacked);packedRanks.change('ranking-date','2026-01-03');await flush();
 check(packedRanks.html.includes('#20')&&!packedRanks.html.includes('#15'),'Compact past snapshot files decode on the Rankings page');
 console.log(`PASS: ${checks} total frontend behavior checks`);
}
hostedChecks().catch(error=>{console.error(error);process.exitCode=1;});
