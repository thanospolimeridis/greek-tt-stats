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
check(render('event/ttscore-777',pairSample,'en').html.includes('A / B'),'Doubles results visible on tournament');
check(render('event/ttscore-777',pairSample,'en').html.includes('individual identities unresolved'),'Unresolved pair identities disclosed');
check(render('player/p1',pairSample,'en').html.includes('100%'),'Doubles do not affect singles statistics');
check(!render('player/p1',pairSample,'en').html.includes('A / B'),'Unresolved pair labels do not create profile history');
pairSample.doubles[0]={...pairSample.doubles[0],player1_id:'p1',partner1_id:'p3',player2_id:'p2',partner2_id:'p4',identity_status:'resolved_members'};
check(render('player/p1',pairSample,'en').html.includes('A / B'),'Resolved doubles appear in member history');
const phasesSample=structuredClone(sample);phasesSample.matches[0].phase='groups';
const phaseView=render('event/ttscore-777',phasesSample,'en');
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
 hosted.meta.release_id='old-release';let interval=0;
 const updated=render('home',hosted,'en',async url=>({ok:true,json:async()=>({release_id:'new-release'})}),
  {setInterval(fn,delay){interval=delay;}});
 await flush();
 check(interval===300000&&updated.html.includes('An updated archive is available.')&&updated.html.includes('Load update'),'Hosted pages announce later releases without automatic navigation');
 console.log(`PASS: ${checks} total frontend behavior checks`);
}
hostedChecks().catch(error=>{console.error(error);process.exitCode=1;});
