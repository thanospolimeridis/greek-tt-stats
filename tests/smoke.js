'use strict';
const fs=require('fs');
const path=require('path');
const vm=require('vm');
const assert=require('assert');
const root=path.join(__dirname,'..');
const script=fs.readFileSync(path.join(root,'src','app.js'),'utf8');
const db=JSON.parse(fs.readFileSync(path.join(root,'data','catalog.json'),'utf8'));
function render(route,data=db){
  const container={innerHTML:''};
  const handlers={};
  const context={
    document:{documentElement:{lang:'el'},getElementById(id){return id==='site-data'?{textContent:JSON.stringify(data)}:id==='app'?container:null},addEventListener(name,fn){handlers[name]=fn}},
    window:{addEventListener(name,fn){handlers[name]=fn},scrollTo(){}},
    localStorage:{getItem(){return 'el'},setItem(){}},
    location:{hash:'#'+route},Intl,URL,encodeURIComponent,decodeURIComponent,console
  };
  vm.runInNewContext(script,context,{timeout:2000});
  return {html:container.innerHTML,handlers,context};
}
assert(render('home').html.includes('Α1 ΑΝΔΡΩΝ 2025-26'),'Home displays sourced events');
assert(render('events').html.includes('ΑΝΟΙΚΤΟ ΠΡΩΤΑΘΛΗΜΑ ΒΟΛΟΥ 2025'),'Event listing works');
assert(render('event/ttscore-777').html.includes('Α1 ΑΝΔΡΩΝ 2025-26'),'Event detail works');
assert(render('players').html.includes('Δεν έχουν εισαχθεί'),'Empty states are honest');
assert(render('rankings').html.includes('Δεν έχουν εισαχθεί'),'Official ranking empty state');
assert(render('h2h').html.includes('σύγκριση'),'H2H empty state');
assert(render('about').html.includes('Διαφάνεια δεδομένων'),'Provenance page works');
const sample=structuredClone(db);
sample.clubs=[{id:'c1',name:'Test Club'}];
sample.players=[{id:'p1',name:'Player One',club_id:'c1'},{id:'p2',name:'Player Two',club_id:'c1'}];
sample.matches=[{id:'m1',event_id:'ttscore-777',date:'2026-02-03',player1_id:'p1',player2_id:'p2',winner_id:'p1',score1:3,score2:1,status:'completed',source_url:'https://app.ttscore.io/test'}];
sample.rankings=[{id:'r1',player_id:'p1',category:'Men',date:'2026-02-03',rank:15,points:99,source_url:'https://app.ttscore.io/test'}];
assert(render('player/p1',sample).html.includes('100%'),'Imported player stats computed');
assert(render('event/ttscore-777',sample).html.includes('Player One'),'Imported match participants shown');
assert(render('rankings',sample).html.includes('Player One'),'Imported official ranking appears');
assert(render('club/c1',sample).html.includes('Player One'),'Club profile works');
const h2h=render('h2h',sample);
assert(h2h.html.includes('Player Two'),'Comparison selections populated');
const switcher=render('home');
switcher.handlers.click({target:{closest(sel){return sel==='#lang-switch'?{}:null}}});
assert(switcher.html.includes('Α1 ΑΝΔΡΩΝ'),'Greek before switch');
console.log('PASS: 12 frontend route/render checks');
