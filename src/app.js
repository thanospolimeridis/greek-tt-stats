(() => {
'use strict';
const db = JSON.parse(document.getElementById('site-data').textContent);
const app = document.getElementById('app');
const dictionary = {
 el:{home:'Αρχική',events:'Διοργανώσεις',players:'Αθλητές',clubs:'Σωματεία',rankings:'Κατατάξεις',h2h:'Head to head',about:'Σχετικά',archive:'ΑΡΧΕΙΟ ΑΓΩΝΩΝ ΕΛΛΑΔΑΣ',heroTitle:'Η ιστορία του ελληνικού',heroHighlight:'πινγκ πονγκ.',heroCopy:'Διοργανώσεις, αγώνες, αθλητές και στατιστικά, σε ένα ενιαίο, ανοικτό αρχείο. Με τεκμηρίωση από τις πρωτογενείς πηγές.',seeEvents:'Εξερεύνηση διοργανώσεων',howItWorks:'Πώς λειτουργεί',sourceEvents:'Διοργανώσεις στο αρχείο',playersIndexed:'Αθλητές με δεδομένα',matchesVerified:'Επαληθευμένοι αγώνες',seasons:'Αγωνιστικές περίοδοι',verifiedSources:'Επαληθευμένες πηγές',dataPending:'Η πρώτη έκδοση περιλαμβάνει πραγματικές καταχωρίσεις διοργανώσεων από το TTScore. Τα αναλυτικά αποτελέσματα, οι αθλητές και οι κατατάξεις δεν έχουν εισαχθεί ακόμη· δεν εμφανίζουμε υποθετικά δεδομένα.',viewSource:'Δείτε στο TTScore',latestEvents:'Αρχείο διοργανώσεων',latestDesc:'Επιλεγμένες, επιβεβαιωμένες εγγραφές με σύνδεσμο στην επίσημη πηγή.',allEvents:'Όλες οι διοργανώσεις',noMatches:'Δεν υπάρχουν ακόμα εισαγμένοι και επαληθευμένοι αγώνες για αυτή τη διοργάνωση.',filterAll:'Όλοι οι τύποι',allSeasons:'Όλες οι περίοδοι',league:'Διασυλλογικό',open:'Open',cup:'Κύπελλο',finals:'Τελική φάση',search:'Αναζήτηση διοργάνωσης, αθλητή ή σωματείου...',date:'Ημερομηνία',region:'Περιοχή',type:'Τύπος',season:'Περίοδος',source:'Πηγή',results:'Αποτελέσματα',sourceRecord:'Πρωτότυπη εγγραφή',details:'Στοιχεία',name:'Όνομα',club:'Σωματείο',rank:'Θέση',points:'Βαθμοί',category:'Κατηγορία',opponent:'Αντίπαλος',score:'Σκορ',round:'Φάση',status:'Κατάσταση',playerHistory:'Ιστορικό αγώνων',rankHistory:'Ιστορικό κατάταξης',wins:'Νίκες',losses:'Ήττες',winRate:'Ποσοστό νικών',filter:'Φίλτρα',noPlayers:'Δεν έχουν εισαχθεί ακόμα εγγραφές αθλητών.',noClubs:'Δεν έχουν εισαχθεί ακόμα εγγραφές σωματείων.',noRankings:'Δεν έχουν εισαχθεί ακόμα επίσημα στιγμιότυπα κατατάξεων.',choosePlayer:'Επιλέξτε αθλητή',compare:'Σύγκριση αθλητών',noH2H:'Δεν υπάρχουν επαληθευμένοι μεταξύ τους αγώνες στη βάση.',selectTwo:'Επιλέξτε δύο διαφορετικούς αθλητές για τη σύγκριση.',missingPlayers:'Η σύγκριση θα ενεργοποιηθεί μετά την εισαγωγή ιστορικών αγώνων.',sourceOnly:'Στοιχεία διοργάνωσης',recorded:'Καταγεγραμμένοι αγώνες',fixtures:'Ομαδικές συναντήσεις',relatedPlayers:'Αθλητές διοργάνωσης',allPlayers:'Κατάλογος αθλητών',allClubs:'Κατάλογος σωματείων',tableEmpty:'Δεν υπάρχουν εγγραφές για αυτή την επιλογή.',overview:'Επισκόπηση',history:'Ιστορικό',view:'Προβολή',verified:'Πηγή επιβεβαιωμένη',statsNotComplete:'Τα στατιστικά αφορούν μόνο τους εισαγμένους αγώνες. Δεν είναι πλήρες ιστορικό καριέρας.',sourcePolicy:'Κάθε αποτέλεσμα διατηρεί τον σύνδεσμο της αρχικής πηγής και ελέγχεται πριν εμφανιστεί.',openData:'Ανοιχτός κώδικας · χωρίς συνδρομές',siteFooter:'Ανεξάρτητο έργο · Δεν αποτελεί επίσημη υπηρεσία της ΕΦΟΕπΑ.',dataTransparency:'Διαφάνεια δεδομένων',dataTransparencyText:'Οι διοργανώσεις καταχωρίζονται με αναφορά στις δημόσιες σελίδες του TTScore. Μέχρι να επαληθευθεί η εισαγωγή των αγώνων, οι αναλύσεις παραμένουν κενές. Οι μεταγενέστερες εισαγωγές ελέγχονται για μοναδικά αναγνωριστικά, βαθμολογίες και πηγές.',architecture:'Απλή αρχιτεκτονική',architectureText:'Στατικά αρχεία HTML και αποτελεσμάτων, Python για τις εισαγωγές και δημοσίευση μέσω GitHub Pages. Δεν απαιτούνται διακομιστής, εμπορική βάση δεδομένων ή εξωτερικές JavaScript βιβλιοθήκες.',importPlan:'Πώς προστίθενται αποτελέσματα',importPlanText:'Με εισαγωγή δομημένων αρχείων CSV (αθλητές, σωματεία, αγώνες, επίσημες κατατάξεις). Ο εισαγωγέας επικυρώνει τις αναφορές και δημιουργεί αυτόματα τον ιστότοπο. Η απευθείας σύνδεση TTScore απαιτεί επιβεβαίωση του τρόπου πρόσβασης.',dataPendingShort:'Σε αναμονή εισαγωγής',loadMore:'Περισσότερα',latestRecords:'Τελευταίες διοργανώσεις',clubFixtures:'Ομαδικές συναντήσεις',individualMatches:'Ατομικοί αγώνες',goBack:'Επιστροφή',noEvents:'Δεν βρέθηκαν διοργανώσεις.',fromSource:'Πηγή: TTScore / ΕΦΟΕπΑ',approx:'Εγγραφές αρχείου',eventsPresent:'Διοργανώσεις σε αυτό το δείγμα',noFixtures:'Δεν υπάρχουν εισαγμένες ομαδικές συναντήσεις.',noRankData:'Δεν υπάρχουν επίσημες κατατάξεις για τον αθλητή.',recordSource:'Προβολή πηγής',howMany:'αποτελέσματα',importStatus:'Κατάσταση κάλυψης'},
 en:{home:'Home',events:'Competitions',players:'Players',clubs:'Clubs',rankings:'Rankings',h2h:'Head to head',about:'About',archive:'GREEK TABLE TENNIS ARCHIVE',heroTitle:'The history of Greek',heroHighlight:'table tennis.',heroCopy:'Competitions, matches, athletes and statistics, all connected in one open, source-attributed archive.',seeEvents:'Explore competitions',howItWorks:'How it works',sourceEvents:'Catalogued competitions',playersIndexed:'Players with data',matchesVerified:'Verified matches',seasons:'Seasons represented',verifiedSources:'Source verified',dataPending:'The first release includes real event listings verified against TTScore. Detailed results, players and rankings have not yet been imported; no results or statistics are invented.',viewSource:'View on TTScore',latestEvents:'Competition archive',latestDesc:'Selected, verified competition listings linking directly to the source.',allEvents:'All competitions',noMatches:'No imported and verified matches for this event yet.',filterAll:'All types',allSeasons:'All seasons',league:'Team league',open:'Open',cup:'Cup',finals:'Finals',search:'Search competitions, players or clubs...',date:'Date',region:'Region',type:'Type',season:'Season',source:'Source',results:'Results',sourceRecord:'Original record',details:'Details',name:'Name',club:'Club',rank:'Rank',points:'Points',category:'Category',opponent:'Opponent',score:'Score',round:'Round',status:'Status',playerHistory:'Match history',rankHistory:'Ranking history',wins:'Wins',losses:'Losses',winRate:'Win percentage',filter:'Filters',noPlayers:'No player records have been imported yet.',noClubs:'No club records have been imported yet.',noRankings:'No official ranking snapshots have been imported yet.',choosePlayer:'Select a player',compare:'Compare players',noH2H:'There are no verified matches between these players in this dataset.',selectTwo:'Select two distinct players to compare.',missingPlayers:'Comparison becomes available when historical match records have been imported.',sourceOnly:'Event metadata',recorded:'Recorded matches',fixtures:'Team fixtures',relatedPlayers:'Competition players',allPlayers:'Player directory',allClubs:'Club directory',tableEmpty:'There are no records matching this selection.',overview:'Overview',history:'History',view:'View',verified:'Source verified',statsNotComplete:'Statistics are based only on imported matches, not necessarily complete career histories.',sourcePolicy:'Every result retains a source link and is checked before publication.',openData:'Open-source · no subscriptions',siteFooter:'Independent project · Not an official service of the Greek federation.',dataTransparency:'Data transparency',dataTransparencyText:'Event listings are associated with their original public TTScore pages. Analytics stay empty until match ingestion is verified. Future imports validate stable identities, scores and source provenance.',architecture:'Simple architecture',architectureText:'Static HTML and result files, Python data imports and publication through GitHub Pages. No application server, commercial database or JavaScript libraries required.',importPlan:'Importing match results',importPlanText:'Structured CSV files for players, clubs, matches and official rankings feed the validator and static site builder. A direct TTScore connector depends on confirming the permitted access/export method.',dataPendingShort:'Awaiting import',loadMore:'Load more',latestRecords:'Latest competitions',clubFixtures:'Team fixtures',individualMatches:'Individual matches',goBack:'Back',noEvents:'No competitions match.',fromSource:'Source: TTScore / HTTF',approx:'Catalogued records',eventsPresent:'Competitions in this sample',noFixtures:'No imported team fixtures.',noRankData:'No official ranking data for this player.',recordSource:'View source',howMany:'results',importStatus:'Data coverage'}
};
Object.assign(dictionary.el, {
 availableThrough:'Μερικά αποτελέσματα έως',notStarted:'Δεν είχε ξεκινήσει στην ημερομηνία αναφοράς',
 noPlayerMatches:'Δεν έχουν εισαχθεί ακόμη ολοκληρωμένοι αγώνες απλού για αυτόν τον αθλητή. Αυτό δεν σημαίνει ότι δεν έχει αγωνιστεί. Οι κατατάξεις εισάγονται ξεχωριστά από το ιστορικό αγώνων.',noDoubles:'Δεν έχουν εισαχθεί αποτελέσματα διπλού για αυτή την επιλογή.',
 categoryViews:'ελεγμένες προβολές φάσης/κατηγορίας',checked:'Ελέγχθηκε',pending:'Σε αναμονή εισαγωγής',deferred:'Αναβλήθηκε',sourceIssues:'Εγγραφές για έλεγχο ή αποκλεισμό',withResults:'Με αποτελέσματα',coverageReport:'Αναφορά κάλυψης',provenanceReport:'Τεκμηρίωση πηγών',notFinished:'Δεν είχε ολοκληρωθεί στην ημερομηνία αναφοράς',undated:'Άγνωστες ημερομηνίες', phaseCategories:'επιλογές φάσης/κατηγορίας',singlesPhase:'Φάση ατομικών',allPhases:'Όλες οι φάσεις',doubles:'Διπλά',groups:'Όμιλοι',knockout:'Νοκ άουτ',consolation:'Παρηγοριά',sourcePairs:'Ονόματα ζευγαριών όπως στην πηγή· χωρίς σύνδεση αθλητών',resolvedPairs:'Τα μέλη του ζευγαριού έχουν ταυτοποιηθεί',completed:'Ολοκληρωμένος',walkover:'Άνευ αγώνα',retired:'Εγκατάλειψη',cancelled:'Ακυρωμένος',scheduled:'Προγραμματισμένος',
 matchesVerified:'Επικυρωμένοι αγώνες',latestDesc:'Διοργανώσεις από τον δημόσιο κατάλογο TTScore. Η κάλυψη αποτελεσμάτων παραμένει μερική.',
 dataPending:'Οι καταχωρίσεις διοργανώσεων δεν αποτελούν πλήρες ιστορικό αποτελεσμάτων. Δεν υπάρχουν εισαγμένα αποτελέσματα για αυτή την επιλογή.',
 dataTransparencyText:'Εισαγωγή από τις δημόσιες φόρμες και τα φύλλα αγώνων του TTScore. Κάθε παρτίδα διατηρεί αιτήματα, χρόνο ανάκτησης και SHA-256. Η επικύρωση ελέγχει τη συνέπεια· δεν πιστοποιεί την ακρίβεια της αρχικής πηγής.',
 legacy:'Παλαιά καταχώριση· απουσιάζει από τον τρέχοντα κατάλογο',verified:'Καταχώριση πηγής',recordSource:'Προβολή πηγής',snapshot:'Στιγμιότυπο',latest:'Τελευταίο ανά κατηγορία',
 games:'Σετ',previous:'Προηγούμενα',next:'Επόμενα',coverage:'Μερική ιστορική κάλυψη',draws:'Ισοπαλίες',
 playerOne:'Πρώτος αθλητής',playerTwo:'Δεύτερος αθλητής',currentRoster:'Σωματείο στο τελευταίο εισαγμένο στιγμιότυπο',
 sourceId:'Αναγνωριστικό πηγής',unknown:'Άγνωστος τύπος',fixtureStats:'Στατιστικά ομαδικών συναντήσεων',
 rankingDate:'Ημερομηνία κατάταξης',importPlanText:'Ο εισαγωγέας Python αποθηκεύει δημόσιες αποκρίσεις, αναγνωρίζει αθλητές με τον αριθμό μητρώου και επικυρώνει CSV. Αμφίβολες εγγραφές αναφέρονται για έλεγχο. Δεν έχουν εισαχθεί όλα τα πρωταθλήματα ή στιγμιότυπα.',
 });
Object.assign(dictionary.en, {
 availableThrough:'Partial results through',notStarted:'Not started by the reference date',
 noPlayerMatches:'No completed singles results have been imported for this player yet. This does not mean they have never played. Rankings are imported separately from match history.',noDoubles:'No doubles results have been imported for this selection.',
 categoryViews:'phase/category views checked',checked:'Checked',pending:'Awaiting import',deferred:'Deferred',sourceIssues:'Records excluded or requiring review',withResults:'With results',coverageReport:'Coverage report',provenanceReport:'Source provenance',notFinished:'Not finished by the reference date',undated:'Unknown dates', phaseCategories:'phase/category selections',singlesPhase:'Singles phase',allPhases:'All phases',doubles:'Doubles',groups:'Groups',knockout:'Knockout',consolation:'Consolation',sourcePairs:'Source pair labels; individual identities unresolved',resolvedPairs:'Pair members identified',completed:'Completed',walkover:'Walkover',retired:'Retired',cancelled:'Cancelled',scheduled:'Scheduled',
 matchesVerified:'Validated matches',latestDesc:'Events from the public TTScore catalog. Result coverage remains partial.',
 dataPending:'Event listings do not constitute a complete results archive. No results have been imported for this selection.',
 dataTransparencyText:'Imported from public TTScore search forms and match sheets. Each batch retains requests, retrieval times and SHA-256 hashes. Validation checks consistency; it does not certify the original source as error-free.',
 legacy:'Legacy listing; absent from current catalog',verified:'Source record',snapshot:'Snapshot',latest:'Latest per category',games:'Games',previous:'Previous',next:'Next',
 coverage:'Partial historical coverage',draws:'Draws',playerOne:'First player',playerTwo:'Second player',
 currentRoster:'Club in latest imported snapshot',sourceId:'Source identifier',unknown:'Unknown type',
 fixtureStats:'Team fixture statistics',rankingDate:'Ranking date',
 importPlanText:'The Python importer caches public responses, links athletes by federation registration number and validates CSV records. Ambiguous records are reported for review. Not all competitions or ranking snapshots have been imported.'
 });
Object.assign(dictionary.el,{kind_individual:"Ατομικό τουρνουά",kind_team_league:"Ομαδικό · βαθμολογία",kind_team_cup:"Ομαδικό · νοκ άουτ",kind_unchecked:"Δεν έχει ελεγχθεί ακόμη",onlyResults:"Μόνο με αποτελέσματα",matchesShort:"αγώνες",playersShort:"αθλητές",eventList:"Λίστα διοργανώσεων",noResultsYet:"Ελέγχθηκε· χωρίς αποτελέσματα απλού",matchesTab:"Αγώνες",winner:"Νικητής",played:"Αγώνες",eventsPlayed:"Συμμετοχές σε διοργανώσεις",bySeason:"Ανά αγωνιστική περίοδο",scope_all:"Όλες οι διοργανώσεις",scope_individual:"Ατομικά τουρνουά",scope_team:"Ομαδικές διοργανώσεις",regNo:"ΑΜ",showMatches:"Αγώνες",allCategories:"Όλες οι κατηγορίες",sortBy:"Ταξινόμηση",sort_rank:"Ταξινόμηση: θέση κατάταξης",sort_played:"Ταξινόμηση: περισσότεροι αγώνες",sort_name:"Ταξινόμηση: αλφαβητικά",anyRanking:"Όλοι οι αθλητές",playerList:"Λίστα αθλητών",unranked:"Χωρίς επίσημη κατάταξη",noMatchesImported:"Χωρίς εισαγμένους αγώνες",record:"Νίκες–Ήττες"});
Object.assign(dictionary.en,{kind_individual:"Individual tournament",kind_team_league:"Team · league table",kind_team_cup:"Team · knockout",kind_unchecked:"Not yet checked",onlyResults:"Only with results",matchesShort:"matches",playersShort:"players",eventList:"Competition list",noResultsYet:"Checked; no singles results",matchesTab:"Matches",winner:"Winner",played:"Played",eventsPlayed:"Competitions played",bySeason:"By season",scope_all:"All competitions",scope_individual:"Individual tournaments",scope_team:"Team competitions",regNo:"Reg.",showMatches:"Matches",allCategories:"All categories",sortBy:"Sort",sort_rank:"Sort: ranking position",sort_played:"Sort: most matches",sort_name:"Sort: name",anyRanking:"All players",playerList:"Player list",unranked:"No official ranking",noMatchesImported:"No imported matches",record:"Won–lost"});
Object.assign(dictionary.el,{chartTitle:"Βαθμοί κατάταξης στο χρόνο",chartTitleRank:"Θέση κατάταξης στο χρόνο",axisPoints:"Βαθμοί",axisRank:"Θέση",range_all:"Όλα",range_1y:"1Ε",range_6m:"6Μ",range_3m:"3Μ",snapshots:"Επίσημα στιγμιότυπα κατάταξης",snapshotsShown:"στιγμιότυπα στο διάστημα",chartNote:"Κάθε σημείο είναι μία δημοσιευμένη κατάταξη της ομοσπονδίας στο TTScore· δεν συμπληρώνονται ενδιάμεσοι μήνες."});
Object.assign(dictionary.en,{chartTitle:"Ranking points over time",chartTitleRank:"Ranking position over time",axisPoints:"Points",axisRank:"Position",range_all:"All",range_1y:"1Y",range_6m:"6M",range_3m:"3M",snapshots:"Official ranking snapshots",snapshotsShown:"snapshots in range",chartNote:"Each point is one published federation ranking on TTScore; months without a snapshot are not filled in."});
const state={phaseFilter:'all',lang:(()=>{try{return localStorage.getItem('tt_lang')==='en'?'en':'el'}catch{return 'el'}})(), query:'', season:'all',type:'all',rankCategory:'all',rankDate:'latest',page:0,player1:'',player2:'',detailTab:'matches',withResults:true,eventTab:'',eventPlayer:'',eventCategory:'all',profileKind:'all',rosterCat:'all',rosterSort:'',chartRange:'1y',chartCat:''};
const t=k=>(dictionary[state.lang][k]||k);
const esc=v=>String(v===undefined||v===null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const lower=v=>String(v||'').toLocaleLowerCase('el-GR');
const romanize=v=>fold(v).replace(/ς/g,'σ').replace(/ου/g,'ou').replace(/αι/g,'ai').replace(/ει/g,'ei').replace(/οι/g,'oi').replace(/γγ/g,'ng').replace(/μπ/g,'b').replace(/ντ/g,'d').replace(/τσ/g,'ts').replace(/τζ/g,'tz').replace(/[αβγδεζηθικλμνξοπρστυφχψω]/g,c=>({'α':'a','β':'v','γ':'g','δ':'d','ε':'e','ζ':'z','η':'i','θ':'th','ι':'i','κ':'k','λ':'l','μ':'m','ν':'n','ξ':'x','ο':'o','π':'p','ρ':'r','σ':'s','τ':'t','υ':'y','φ':'f','χ':'ch','ψ':'ps','ω':'o'}[c]||c));
const fold=v=>String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('el-GR').replace(/ς/g,'σ');
const searchHit=(obj,q)=>!q||[obj.name,obj.region,obj.season,obj.aliases,obj.category,obj.type].filter(Boolean).some(v=>fold(v).includes(fold(q))||fold(romanize(v)).includes(fold(q)));
const datefmt=v=>{if(!v)return '—';const d=new Date(v+'T12:00:00Z');return Number.isNaN(d.getTime())?esc(v):new Intl.DateTimeFormat(state.lang==='el'?'el-GR':'en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(d)};
const eventById=new Map(db.events.map(v=>[v.id,v]));
const playerById=new Map(db.players.map(v=>[v.id,v]));
const clubById=new Map(db.clubs.map(v=>[v.id,v]));
let records=[];
const matchesByEvent=new Map(),matchesByPlayer=new Map(),completedByEvent=new Map();
function indexResults(){
 records=db.matches.filter(m=>m.status==='completed');
 matchesByEvent.clear();matchesByPlayer.clear();completedByEvent.clear();
 for(const [id,count] of Object.entries(db.meta.event_match_counts||{}))completedByEvent.set(id,count);
 for(const m of db.matches){
 if(!matchesByEvent.has(m.event_id))matchesByEvent.set(m.event_id,[]);
 matchesByEvent.get(m.event_id).push(m);
 for(const id of [m.player1_id,m.player2_id]){if(!matchesByPlayer.has(id))matchesByPlayer.set(id,[]);matchesByPlayer.get(id).push(m);}
 if(m.status==='completed'&&!db.meta.event_match_counts)completedByEvent.set(m.event_id,(completedByEvent.get(m.event_id)||0)+1);
 }
}
indexResults();
const totalSingles=()=>db.meta.verified_results??records.length;
const totalDoubles=()=>db.meta.table_counts?.doubles??(db.doubles||[]).length;

// The hosted site loads one public static result file per detail view. The
// portable page has no partitions and follows the original synchronous path.
const resultCache=new Map();
let activePart=null,pendingPart=null,loadVersion=0,loadError=false,updateAvailable=false;
function updateNotice(){
 if(!updateAvailable)return '';
 const el=state.lang==='el';
 return `<div class="container"><div class="statusbox" role="status"><span>${el?'Υπάρχουν νεότερα δεδομένα στο αρχείο.':'An updated archive is available.'}</span><button class="ghost-btn small" id="archive-update">${el?'Φόρτωση νέας έκδοσης':'Load update'}</button></div></div>`;
}
async function checkForUpdate(){
 if(updateAvailable)return;
 try{
  const response=await fetch('version.json',{cache:'no-store'});
  if(!response.ok)return;
  const version=await response.json();
  if(typeof version.release_id==='string'&&version.release_id!==db.meta.release_id){
   updateAvailable=true;
   // Do not interrupt a search or an open filter while announcing new data.
   if(!document.activeElement?.matches('input,select,textarea'))render();
  }
 }catch{/* A failed update check must not interrupt the current archive. */}
}
function useResults(payload){
 for(const kind of ['matches','doubles','fixtures'])db[kind]=payload[kind];
 indexResults();
}
function prepareResults(route){
 const parts=db.meta.partitions;if(!parts)return false;
 const kind=route.view==='h2h'?'player':route.view;
 const id=route.view==='h2h'?state.player1:route.id;
 const part=parts[kind]?.[id]||'';
 if(pendingPart!==null&&pendingPart!==part){loadVersion++;pendingPart=null;}
 if(activePart===part)return false;
 if(!part){useResults({matches:[],doubles:[],fixtures:[]});activePart='';return false;}
 if(resultCache.has(part)){
  const payload=resultCache.get(part);resultCache.delete(part);resultCache.set(part,payload);
  useResults(payload);activePart=part;return false;
 }
 if(pendingPart!==part){
  pendingPart=part;loadError=false;const version=++loadVersion;
  fetch(part).then(response=>{if(!response.ok)throw new Error('Result request failed');return response.json();}).then(payload=>{
   if(!['matches','doubles','fixtures'].every(k=>Array.isArray(payload[k])))throw new Error('Invalid result file');
   if(version!==loadVersion)return;
   resultCache.set(part,payload);
   if(resultCache.size>8)resultCache.delete(resultCache.keys().next().value);
   useResults(payload);activePart=part;pendingPart=null;render();
  }).catch(()=>{if(version===loadVersion){loadError=true;render();}});
 }
 const el=state.lang==='el';
 const message=loadError?(el?'Δεν ήταν δυνατή η φόρτωση των αποτελεσμάτων. Ανανεώστε τη σελίδα για νέα προσπάθεια.':'Results could not be loaded. Reload the page to try again.'):(el?'Φόρτωση αποτελεσμάτων…':'Loading results…');
 app.innerHTML=header()+updateNotice()+`<main class="container main"><div class="white-panel" role="${loadError?'alert':'status'}"><p>${esc(message)}</p>${loadError?`<button class="ghost-btn" id="archive-reload">${el?'Ανανέωση σελίδας':'Reload page'}</button>`:''}</div></main>`+footer();
 return true;
}

const getPlayer=id=>playerById.get(id)||{name:id||'—',id};
const getClub=id=>clubById.get(id)||{name:id||'—',id};
const getEvent=id=>eventById.get(id)||{name:id||'—',id};
const eventName=e=>esc(e.name||'—');
const link=(href,label,css='text-link')=>`<a class="${css}" href="${esc(href)}">${esc(label)}</a>`;
const external=(url,label)=>url&&/^https:\/\/[^\s"<>]+$/.test(url)?`<a class="text-link" href="${esc(url)}" rel="noopener noreferrer" target="_blank">${esc(label)} ↗</a>`:'';
const seasons=[...new Set(db.events.map(e=>e.season).filter(Boolean))].sort().reverse();
function hashRoute(){let hash;try{hash=decodeURIComponent(location.hash.replace(/^#\/?/,''))}catch{return {view:'404',id:''}};const [view, ...parts]=(hash||'home').split('/');return{view: view||'home', id:parts.join('/')};}
function navActive(name){const r=hashRoute();return r.view===name||(name==='events'&&r.view==='event')||(name==='players'&&r.view==='player')||(name==='clubs'&&r.view==='club')?'active':'';}
function header(){const items=['home','events','players','clubs','rankings','h2h'];return `<header class="topbar"><div class="container top-inner"><a href="#home" class="brand" aria-label="Greek TT Archive"><span class="brandmark"><span>◉</span></span><span><span class="brandtitle">GREEK TT <span style="color:#89dccc">ARCHIVE</span></span><span class="brandunder">ΕΠΙΤΡΑΠΕΖΙΑ ΑΝΤΙΣΦΑΙΡΙΣΗ</span></span></a><nav class="nav" aria-label="Main navigation">${items.map((k,i)=>`<a href="#${k}" class="navlink ${navActive(k)} ${i===1?'navmobile':''}">${esc(t(k))}</a>`).join('')}<button id="lang-switch" class="lang" aria-label="Switch language">${state.lang==='el'?'EN':'ΕΛ'}</button></nav></div></header>`;}
function footer(){return `<footer class="footer"><div class="container footer-inner"><div><strong>Greek TT Archive</strong><p>${esc(t('siteFooter'))}</p></div><div><div class="footer-code">${esc(t('openData'))}</div><p>${external('https://app.ttscore.io/customer/24','TTScore')} · ${link('#about',t('dataTransparency'))}</p></div></div></footer>`;}
function hero(){return `<section class="hero"><div class="container heroinner"><div class="herocopy"><div class="eyebrow"><span class="tiny-dot"></span>${esc(t('archive'))}</div><h1>${esc(t('heroTitle'))}<br><strong>${esc(t('heroHighlight'))}</strong></h1><p>${esc(t('heroCopy'))}</p><div class="heroact"><a class="primary-btn" href="#events">${esc(t('seeEvents'))} →</a><a class="light-btn" href="#about">${esc(t('howItWorks'))} ↗</a></div></div><div class="heroart" aria-hidden="true"><div class="court"></div><div class="racket"></div><div class="ball"></div></div></div></section>`;}
function statsBand(){const values=[[db.events.length,'sourceEvents'],[db.players.length,'playersIndexed'],[totalSingles(),'matchesVerified'],[seasons.length,'seasons']];return `<section class="container stats-band" aria-label="Archive coverage">${values.map(([v,k])=>`<div class="stat"><div class="statnum">${v.toLocaleString(state.lang==='el'?'el-GR':'en-US')}</div><div class="statlabel">${esc(t(k))}</div></div>`).join('')}</section>`;}
function statusBox(message){return `<div class="statusbox" role="status"><span class="circle">ⓘ</span><div><strong>${esc(t('coverage'))}:</strong> ${esc(t(message||(totalSingles()?'statsNotComplete':'dataPending')))}</div></div>`;}
function paginate(rows){const size=50;const pages=Math.max(1,Math.ceil(rows.length/size));state.page=Math.max(0,Math.min(state.page,pages-1));return {rows:rows.slice(state.page*size,(state.page+1)*size),controls:pages>1?`<div class="filters"><button class="ghost-btn small" id="page-prev" ${state.page===0?'disabled':''}>${esc(t('previous'))}</button><span>${state.page+1} / ${pages} · ${rows.length}</span><button class="ghost-btn small" id="page-next" ${state.page===pages-1?'disabled':''}>${esc(t('next'))}</button></div>`:''};}
function eventCard(e){const linked=completedByEvent.get(e.id)||0;return `<article class="event-card"><div class="event-card-top">${kindTag(e)}<span class="date">${esc(e.season)}</span></div><h3><a href="#event/${encodeURIComponent(e.id)}">${eventName(e)}</a></h3><div class="event-card-meta"><span>⌖ ${esc(e.region||'—')}</span><span>◷ ${datefmt(e.start_date)}</span></div><div class="event-card-foot"><a class="text-link" href="#event/${encodeURIComponent(e.id)}">${esc(t('details'))} →</a><span class="smallmuted">${linked?`${linked} ${esc(t('matchesShort'))} · ${eventPlayers(e.id)} ${esc(t('playersShort'))}`:esc(t('sourceOnly'))}</span></div></article>`;}
function filteredEvents(kind=state.type){return db.events.filter(e=>(state.season==='all'||e.season===state.season)&&(kind==='all'||eventKind(e)===kind)&&(!state.withResults||(completedByEvent.get(e.id)||0)>0)&&searchHit(e,state.query));}
function eventFilters(){const kinds=['all',...EVENT_KINDS];return `<div class="searchpanel"><div class="filters" style="margin:0"><label class="sr-only" for="search-events">${esc(t('search'))}</label><input class="control" type="search" id="search-events" placeholder="${esc(t('search'))}" value="${esc(state.query)}"><label class="sr-only" for="season-filter">${esc(t('season'))}</label><select class="control" id="season-filter"><option value="all">${esc(t('allSeasons'))}</option>${seasons.map(s=>`<option value="${esc(s)}" ${s===state.season?'selected':''}>${esc(s)}</option>`).join('')}</select><label class="checkline"><input type="checkbox" id="results-only" ${state.withResults?'checked':''}> ${esc(t('onlyResults'))}</label></div><div class="kind-chips" role="group" aria-label="${esc(t('type'))}">${kinds.map(k=>`<button type="button" class="chip ${state.type===k?'active':''}" data-kind="${k}" aria-pressed="${state.type===k}">${k==='all'?esc(t('filterAll')):`<i class="dot kind-${k}"></i>${esc(t('kind_'+k))}`} · ${filteredEvents(k).length}</button>`).join('')}</div></div>`;}
function eventsSection(){const rows=filteredEvents(),page=paginate(rows),from=state.page*50;return `<div class="list-head"><span class="list-title">${esc(t('eventList'))}</span><span class="smallmuted">${rows.length?`${from+1}–${from+page.rows.length} / ${rows.length}`:''}</span></div>`+(page.rows.length?`<div class="event-list">${page.rows.map(eventRow).join('')}</div>${page.controls}`:empty('noEvents'));}
function empty(k,icon='◌'){return `<div class="empty"><div class="empty-icon" aria-hidden="true">${icon}</div><h3>${esc(t('dataPendingShort'))}</h3><p>${esc(t(k))}</p><a class="ghost-btn small" href="#about">${esc(t('howItWorks'))} →</a></div>`;}
function landing(){const n=db.events.length;return hero()+statsBand()+`<main class="container main">${statusBox()}<div class="paneltop"><div><span class="kicker">${esc(t('latestRecords'))}</span><h2>${esc(t('latestEvents'))}</h2><p>${esc(t('latestDesc'))}</p></div><a class="ghost-btn small" href="#events">${esc(t('allEvents'))} →</a></div>${db.events.length?`<div class="cards">${db.events.slice(0,6).map(eventCard).join('')}</div>`:empty('noEvents')}<div class="info-grid"><section class="white-panel"><span class="kicker">${esc(t('dataTransparency'))}</span><h3>${esc(t('sourcePolicy'))}</h3><p>${esc(t('dataTransparencyText'))}</p><div class="link-row">${external('https://app.ttscore.io/customer/24',t('viewSource'))}</div></section><section class="white-panel"><span class="kicker">${esc(t('approx'))}</span><h3>${n} ${esc(t('eventsPresent'))}</h3><p>${esc(t('architectureText'))}</p><a href="#about" class="text-link">${esc(t('howItWorks'))} →</a></section></div></main>`;}
function crumb(parts){return `<div class="breadcrumbs">${parts.map((p,i)=>i===parts.length-1?`<span>${esc(p[1])}</span>`:`<a href="#${esc(p[0])}">${esc(p[1])}</a><span>›</span>`).join('')}</div>`;}
function eventsPage(){return `<main class="container main">${crumb([['home',t('home')],['events',t('events')]])}${sectionSwitch('events')}${eventFilters()}${statusBox()}${eventsSection()}</main>`;}
function completedForPlayer(id){return (matchesByPlayer.get(id)||[]).filter(m=>m.status==='completed')}
function playerStats(id){const ms=completedForPlayer(id);const wins=ms.filter(m=>m.winner_id===id).length;return{ms,wins,losses:ms.length-wins,rate:ms.length?Math.round(wins/ms.length*100):null}}
function dataTable(headers,rows,emptyKey='tableEmpty'){return rows.length?`<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th scope="col">${esc(t(h))}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`:empty(emptyKey)}
function matchRow(m,id){
 const reverse=id===m.player2_id;
 const counterpart=id?(reverse?m.player1_id:m.player2_id):null;
 const scores=reverse?[m.score2,m.score1]:[m.score1,m.score2];
 const score=scores.every(v=>v!==null&&v!==undefined&&v!=='')?scores.join('–'):'—';
 const games=(m.games||[]).map(g=>(reverse?[g[1],g[0]]:g).join('–')).join(', ');
 const result=id&&m.status==='completed'?(m.winner_id===id?'✓':'✕'):'';
 return `<tr><td>${datefmt(m.date)}</td><td>${id?link('#player/'+encodeURIComponent(counterpart),getPlayer(counterpart).name):link('#player/'+encodeURIComponent(m.player1_id),getPlayer(m.player1_id).name)+' <span class="smalltext">vs</span> '+link('#player/'+encodeURIComponent(m.player2_id),getPlayer(m.player2_id).name)}</td><td><span class="score">${esc(result)} ${esc(score)}</span>${games?`<details><summary>${esc(t('games'))}</summary>${esc(games)}</details>`:''}<div class="smalltext">${esc(t(m.status))}</div></td><td>${link('#event/'+encodeURIComponent(m.event_id),getEvent(m.event_id).name)}<div class="smalltext">${esc(t(m.phase||'league'))} · ${esc(m.category||'')}</div></td><td>${external(m.source_url,t('source'))}</td></tr>`;
}
function fixturesTable(fixtures){return dataTable(['date','club','score','opponent','source'],fixtures.map(f=>`<tr><td>${datefmt(f.date)}</td><td>${link('#club/'+encodeURIComponent(f.home_club_id),getClub(f.home_club_id).name)}</td><td><span class="score">${f.home_score??'—'}–${f.away_score??'—'}</span><div class="smalltext">${esc(t(f.status))}</div></td><td>${link('#club/'+encodeURIComponent(f.away_club_id),getClub(f.away_club_id).name)}</td><td>${external(f.source_url,t('source'))}</td></tr>`),'noFixtures');}
function doublesTable(rows){return dataTable(['date','players','score','events','source'],rows.map(m=>`<tr><td>${datefmt(m.date)}</td><td>${esc(m.side1_name)}<br>vs<br>${esc(m.side2_name)}<div class="smalltext">${esc(t(m.identity_status==='resolved_members'?'resolvedPairs':'sourcePairs'))}</div></td><td><span class="score">${m.score1}–${m.score2}</span><details><summary>${esc(t('games'))}</summary>${(m.games||[]).map(g=>g.join('–')).join(', ')}</details></td><td>${link('#event/'+encodeURIComponent(m.event_id),getEvent(m.event_id).name)}<div>${esc(t(m.phase||'doubles'))}${m.category?' · '+esc(m.category):''}</div></td><td>${external(m.source_url,t('source'))}</td></tr>`),'noDoubles');}
function eventPage(id){
 const e=eventById.get(id);if(!e)return notFound();
 const kind=eventKind(e),all=matchesByEvent.get(id)||[];
 const cats=[...new Set(all.map(m=>m.category).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'el'));
 if(state.eventCategory!=='all'&&!cats.includes(state.eventCategory))state.eventCategory='all';
 const inCat=all.filter(m=>state.eventCategory==='all'||m.category===state.eventCategory);
 const fs=db.fixtures.filter(f=>f.event_id===id),ds=(db.doubles||[]).filter(m=>m.event_id===id);
 const summary=eventSummary(inCat),completed=all.filter(m=>m.status==='completed');
 const tabs=[['players',summary.length],['matches',all.length],['doubles',ds.length],['fixtures',fs.length]].filter(([key,n])=>n||key==='matches');
 const tab=tabs.some(([key])=>key===state.eventTab)?state.eventTab:summary.length?'players':'matches';
 const dates=e.start_date&&e.end_date&&e.start_date!==e.end_date?`${datefmt(e.start_date)} – ${datefmt(e.end_date)}`:datefmt(e.start_date||e.end_date);
 const catFilter=cats.length>1&&(tab==='players'||tab==='matches')?`<label for="event-category">${esc(t('category'))}</label><select id="event-category" class="control"><option value="all">${esc(t('allCategories'))}</option>${cats.map(c=>`<option value="${esc(c)}" ${c===state.eventCategory?'selected':''}>${esc(c)}</option>`).join('')}</select>`:'';
 let body='';
 if(tab==='players'){const page=paginate(summary);body=`${catFilter?`<div class="filters">${catFilter}</div>`:''}<div class="player-list">${page.rows.map(eventPlayerRow).join('')}</div>${page.controls}`;}
 else if(tab==='matches'){
  const phases=[...new Set(all.map(m=>m.phase||'league'))];
  const ms=inCat.filter(m=>(state.phaseFilter==='all'||(m.phase||'league')===state.phaseFilter)&&(!state.eventPlayer||m.player1_id===state.eventPlayer||m.player2_id===state.eventPlayer));
  const page=paginate(ms);
  body=`<div class="filters">${phases.length>1||phases[0]!=='league'?`<label for="phase-filter">${esc(t('singlesPhase'))}</label><select id="phase-filter" class="control"><option value="all">${esc(t('allPhases'))}</option>${phases.map(p=>`<option value="${esc(p)}" ${p===state.phaseFilter?'selected':''}>${esc(t(p))}</option>`).join('')}</select>`:''}${catFilter}${state.eventPlayer?`<button type="button" class="chip active" data-event-player="">${esc(getPlayer(state.eventPlayer).name)} ✕</button>`:''}<span class="smallmuted">${ms.length} ${esc(t('matchesShort'))}</span></div>${page.rows.length?`<div class="match-list">${page.rows.map(matchCard).join('')}</div>`:empty('noMatches')}${page.controls}`;
 }
 else if(tab==='doubles')body=doublesTable(ds);
 else body=fixturesTable(fs);
 return `<main class="container main">${crumb([['home',t('home')],['events',t('events')],['event/'+id,e.name]])}<div class="detailhead"><div class="detailhead-top"><div class="detail-title-area"><span class="kicker">${esc(t('kind_'+kind))} · ${esc(e.season)}</span><h1 class="title-detail">${eventName(e)}</h1><div class="detail-chips">${kindTag(e)}<span>◷ ${dates}</span><span>⌖ ${esc(e.region||'—')}</span></div><div class="proof">✓ ${esc(t(e.source_status==='legacy_not_in_current_catalog'?'legacy':'verified'))} · TTScore</div></div><div>${external(e.source_url,t('viewSource'))}</div></div></div><div class="results-grid"><div class="metric"><span>${esc(t('individualMatches'))}</span><strong>${completed.length}</strong></div><div class="metric"><span>${esc(t('players'))}</span><strong>${eventSummary(all).length}</strong></div><div class="metric"><span>${esc(t(fs.length?'clubFixtures':'doubles'))}</span><strong>${fs.length||ds.length}</strong></div></div><div class="subtabs" role="tablist">${tabs.map(([key,n])=>`<button type="button" role="tab" id="tab-${key}" class="subtab ${key===tab?'active':''}" aria-selected="${key===tab}">${esc(t(key==='players'?'players':key==='matches'?'matchesTab':key==='doubles'?'doubles':'clubFixtures'))} <span class="tabcount">${n}</span></button>`).join('')}</div>${body}${eventCoverageNote(e)}<p class="source-note" style="margin-top:22px">${esc(t('statsNotComplete'))} ${external(e.source_url,t('recordSource'))}</p></main>`;
}
function rosterPage(kind){const isPlayer=kind==='players';const data=isPlayer?db.players:db.clubs;const title=isPlayer?t('allPlayers'):t('allClubs');const page=paginate(data.filter(v=>searchHit(v,state.query)).sort((a,b)=>a.name.localeCompare(b.name,'el')));const list=page.rows;return `<main class="container main">${crumb([['home',t('home')],[kind,t(kind)]])}<div class="paneltop"><div><span class="kicker">${esc(t('archive'))}</span><h2>${esc(title)}</h2></div></div>${statusBox()}<div class="filters"><label class="sr-only" for="search-roster">${esc(t('search'))}</label><input class="control" type="search" id="search-roster" placeholder="${esc(t('search'))}" value="${esc(state.query)}"></div>${list.length?`<div class="cards">${list.map(v=>`<a href="#${isPlayer?'player':'club'}/${encodeURIComponent(v.id)}" class="${isPlayer?'person-card':'club-card'}"><div class="listmain"><div class="round-icon">${esc((v.name||'?').charAt(0))}</div><div><div class="listname">${esc(v.name)}</div><div class="listmeta">${isPlayer?esc(getClub(v.club_id).name):esc(v.region||'')}</div></div></div><div class="event-card-foot" style="margin-top:19px"><span class="text-link">${esc(t('view'))} →</span></div></a>`).join('')}</div>`:empty(isPlayer?'noPlayers':'noClubs')}${page.controls}</main>`;}
function latestRanking(id){return db.rankings.filter(r=>r.player_id===id).sort((a,b)=>b.date.localeCompare(a.date))[0]}
function playerPage(id){
 const p=playerById.get(id);if(!p)return notFound();
 const allMs=[...(matchesByPlayer.get(id)||[])].sort((a,b)=>b.date.localeCompare(a.date));
 const scopeOf=m=>{const k=eventKind(getEvent(m.event_id));return TEAM_KINDS.includes(k)?'team':k};
 const inScope=m=>state.profileKind==='all'||scopeOf(m)===state.profileKind;
 const ms=allMs.filter(inScope),done=ms.filter(m=>m.status==='completed');
 const wins=done.filter(m=>m.winner_id===id).length,losses=done.length-wins,rate=done.length?Math.round(wins/done.length*100):null;
 const scopeCount=k=>allMs.filter(m=>m.status==='completed'&&(k==='all'||scopeOf(m)===k)).length;
 const ranks=db.rankings.filter(r=>r.player_id===id).sort((a,b)=>b.date.localeCompare(a.date));const latest=ranks[0];
 const bySeason=new Map(),byEvent=new Map();
 for(const m of done){const ev=getEvent(m.event_id),s=ev.season||'—';
  const row=bySeason.get(s)||{events:new Set(),played:0,won:0};row.events.add(m.event_id);row.played++;if(m.winner_id===id)row.won++;bySeason.set(s,row);
  const er=byEvent.get(m.event_id)||{ev,last:m.date,played:0,won:0};er.played++;if(m.winner_id===id)er.won++;if(m.date>er.last)er.last=m.date;byEvent.set(m.event_id,er);}
 const seasonRows=[...bySeason.entries()].sort((a,b)=>b[0].localeCompare(a[0])).map(([s,r])=>`<tr><td>${esc(s)}</td><td>${r.events.size}</td><td>${r.played}</td><td>${r.won}</td><td>${r.played-r.won}</td><td>${Math.round(r.won/r.played*100)}%</td></tr>`);
 const eventRows=[...byEvent.values()].sort((a,b)=>b.last.localeCompare(a.last)).map(r=>`<tr><td>${datefmt(r.last)}</td><td>${link('#event/'+encodeURIComponent(r.ev.id),r.ev.name)}<div class="smalltext">${esc(r.ev.season||'')}</div></td><td>${kindTag(r.ev)}</td><td>${r.played}</td><td><span class="score">${r.won}–${r.played-r.won}</span></td></tr>`);
 const page=paginate(ms);
 const scopes=['all','individual','team'].map(k=>`<button type="button" id="scope-${k}" class="seg-btn ${state.profileKind===k?'active':''}" aria-pressed="${state.profileKind===k}">${esc(t('scope_'+k))} · ${scopeCount(k)}</button>`).join('');
 return `<main class="container main">${crumb([['home',t('home')],['players',t('players')],['player/'+id,p.name]])}<div class="detailhead"><div class="detailhead-top"><div class="profile-head"><div class="avatar big">${esc(initials(p.name))}</div><div class="detail-title-area"><span class="kicker">${esc(regNo(id)||t('players'))}</span><h1 class="title-detail">${esc(p.name)}</h1><div class="detail-chips"><span>♧ ${esc(getClub(p.club_id).name)}${p.club_as_of?' · '+datefmt(p.club_as_of):''}</span>${latest?`<span>${esc(t('rank'))}: #${latest.rank} · ${esc(latest.category)}${latest.points!=null?' · '+esc(fmtPoints(latest.points))+' '+esc(t('points')):''} · ${datefmt(latest.date)}</span>`:''}</div></div></div><a class="ghost-btn small" href="#h2h">${esc(t('compare'))} →</a></div></div>${rankingSection(ranks)}${statusBox(done.length?'statsNotComplete':'noPlayerMatches')}<div class="seg seg-wide" role="group" aria-label="${esc(t('type'))}">${scopes}</div><div class="results-grid"><div class="metric"><span>${esc(t('wins'))}</span><strong>${done.length?wins:'—'}</strong></div><div class="metric"><span>${esc(t('losses'))}</span><strong>${done.length?losses:'—'}</strong></div><div class="metric"><span>${esc(t('winRate'))}</span><strong>${rate===null?'—':rate+'%'}</strong></div></div>${done.length?`<div class="profile-grid"><section><div class="section-header"><h3>${esc(t('bySeason'))}</h3></div>${dataTable(['season','events','played','wins','losses','winRate'],seasonRows)}</section><section><div class="section-header"><h3>${esc(t('eventsPlayed'))} · ${byEvent.size}</h3></div>${dataTable(['date','events','type','played','record'],eventRows)}</section></div>`:''}<div class="section-header"><h3>${esc(t('playerHistory'))}</h3></div>${dataTable(['date','opponent','score','events','source'],page.rows.map(m=>matchRow(m,id)),'noPlayerMatches')}${page.controls}<div class="section-header"><h3>${esc(t('doubles'))}</h3></div>${doublesTable((db.doubles||[]).filter(m=>[m.player1_id,m.partner1_id,m.player2_id,m.partner2_id].includes(id)))}<p class="source-note" style="margin-top:22px">${esc(t('statsNotComplete'))}</p></main>`;
}
function clubPage(id){const c=clubById.get(id);if(!c)return notFound();const ps=db.players.filter(p=>p.club_id===id);const fs=db.fixtures.filter(f=>f.home_club_id===id||f.away_club_id===id);const done=fs.filter(f=>f.status==='completed');const wins=done.filter(f=>f.home_club_id===id?f.home_score>f.away_score:f.away_score>f.home_score).length;const draws=done.filter(f=>f.home_score===f.away_score).length;return `<main class="container main">${crumb([['home',t('home')],['clubs',t('clubs')],['club/'+id,c.name]])}<div class="detailhead"><span class="kicker">${esc(t('clubs'))}</span><h1 class="title-detail">${esc(c.name)}</h1><p>${esc(c.region||'')}</p></div>${statusBox()}<h3>${esc(t('fixtureStats'))}</h3><div class="results-grid"><div class="metric"><span>${esc(t('wins'))}</span><strong>${wins}</strong></div><div class="metric"><span>${esc(t('losses'))}</span><strong>${done.length-wins-draws}</strong></div><div class="metric"><span>${esc(t('draws'))}</span><strong>${draws}</strong></div></div><div class="section-header"><h3>${esc(t('currentRoster'))} · ${ps.length}</h3></div>${ps.length?`<div class="white-panel">${ps.map(p=>`<div class="listrow"><div class="listmain"><div class="round-icon">${esc(p.name.charAt(0))}</div><div class="listname">${esc(p.name)}</div></div>${link('#player/'+encodeURIComponent(p.id),t('view')+' →')}</div>`).join('')}</div>`:empty('noPlayers')}<div class="section-header"><h3>${esc(t('clubFixtures'))}</h3></div>${fixturesTable(fs)}</main>`;}
function rankingsPage(){const cats=[...new Set(db.rankings.map(r=>r.category))].sort();const data=db.rankings.filter(r=>state.rankCategory==='all'||r.category===state.rankCategory);const datesByCat=new Map();for(const r of data){const last=datesByCat.get(r.category);if(!last||last<r.date)datesByCat.set(r.category,r.date)}const dates=[...new Set(data.map(r=>r.date))].sort().reverse();const page=paginate(data.filter(r=>state.rankDate==='latest'?datesByCat.get(r.category)===r.date:r.date===state.rankDate).sort((a,b)=>a.category.localeCompare(b.category)||a.rank-b.rank));const current=page.rows;return `<main class="container main">${crumb([['home',t('home')],['rankings',t('rankings')]])}<div class="paneltop"><div><span class="kicker">${esc(t('fromSource'))}</span><h2>${esc(t('rankings'))}</h2><p>${esc(t('statsNotComplete'))}</p></div></div>${statusBox()}${cats.length?`<div class="filters"><label for="ranking-category">${esc(t('category'))}:</label><select id="ranking-category" class="control"><option value="all">${esc(t('category'))}: ${esc(t('filterAll'))}</option>${cats.map(c=>`<option value="${esc(c)}" ${c===state.rankCategory?'selected':''}>${esc(c)}</option>`).join('')}</select><label for="ranking-date">${esc(t('rankingDate'))}</label><select id="ranking-date" class="control"><option value="latest">${esc(t('latest'))}</option>${dates.map(d=>`<option value="${d}" ${d===state.rankDate?'selected':''}>${datefmt(d)}</option>`).join('')}</select></div>`:''}${dataTable(['rank','name','category','points','date','source'],current.map(r=>`<tr><td><strong>#${r.rank}</strong></td><td>${link('#player/'+encodeURIComponent(r.player_id),getPlayer(r.player_id).name)}</td><td>${esc(r.category)}</td><td>${r.points??'—'}</td><td>${datefmt(r.date)}</td><td>${external(r.source_url,t('source'))}</td></tr>`),'noRankings')}${page.controls}</main>`;}
function h2hPage(){const opts=`<option value="">${esc(t('choosePlayer'))}</option>`+db.players.slice().sort((a,b)=>a.name.localeCompare(b.name,'el')).map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('');const id1=state.player1,id2=state.player2;const both=id1&&id2&&id1!==id2;const meetings=both?completedForPlayer(id1).filter(m=>[m.player1_id,m.player2_id].includes(id2)):[];const w1=meetings.filter(m=>m.winner_id===id1).length,w2=meetings.filter(m=>m.winner_id===id2).length;return `<main class="container main">${crumb([['home',t('home')],['h2h',t('h2h')]])}<div class="paneltop"><div><span class="kicker">${esc(t('players'))}</span><h2>${esc(t('compare'))}</h2><p>${esc(t('statsNotComplete'))}</p></div></div><div class="white-panel"><div class="compare-selects"><select id="h2h-player1" aria-label="${esc(t('playerOne'))}">${opts}</select><div class="versus">VS</div><select id="h2h-player2" aria-label="${esc(t('playerTwo'))}">${opts}</select></div>${both?`<div class="compareline"><span>${esc(getPlayer(id1).name)} · ${w1}</span><span>${w2} · ${esc(getPlayer(id2).name)}</span></div><div class="comparebar"><span style="width:${meetings.length?100*w1/meetings.length:50}%"></span><span style="width:${meetings.length?100*w2/meetings.length:50}%"></span></div>${dataTable(['date','opponent','score','events','source'],meetings.sort((a,b)=>b.date.localeCompare(a.date)).map(m=>matchRow(m,id1)),'noH2H')}}`:empty(db.players.length<2?'missingPlayers':'selectTwo')}</div></main>`;}
function coverageRecord(event){
 const c=db.meta.provenance?.coverage||{},id=event.id.replace(/^ttscore-/,'');
 if(c.events?.[id])return c.events[id];
 if(c.leagues?.[id]){const l=c.leagues[id];return {singles:l.singles_imported,doubles:l.doubles_imported||0,fixtures:l.fixtures_imported,issues:l.review_rows||0,phases:['league'],status:l.status};}
 return null;
}
function eventCoverageNote(event){
 const c=coverageRecord(event),deferred=db.meta.provenance?.coverage?.batch?.deferred?.find(e=>'ttscore-'+e.event===event.id);
 if(c)return `<p class="source-note">${esc(t('checked'))} · ${c.issues||0} ${esc(t('sourceIssues'))}.${c.scope==='available_results'?` ${esc(t('availableThrough'))} ${datefmt(c.snapshot_date)}.`:''} ${link('#about',t('coverageReport'))}</p>`;
 return `<p class="source-note">${esc(deferred?t(deferred.reason==='undated'?'undated':deferred.reason==='not_started_by_cutoff'?'notStarted':'notFinished'):t('pending'))}. ${link('#about',t('coverageReport'))}</p>`;
}
function coverageDetails(){
 const coverage=db.meta.provenance?.coverage;if(!coverage)return '';
 const el=state.lang==='el',batch=coverage.batch;
 const filtered=db.events.filter(e=>(state.season==='all'||e.season===state.season)&&searchHit(e,state.query));
 const page=paginate(filtered);
 const deferred=new Map((batch?.deferred||[]).map(e=>['ttscore-'+e.event,e]));
 const summary=Object.entries(db.meta.season_coverage||{}).map(([season,c])=>{
  const events=db.events.filter(e=>e.season===season);
  return `<tr><td>${esc(season)}</td><td>${events.filter(e=>coverageRecord(e)).length}/${c.catalog_events}</td><td>${events.filter(e=>deferred.has(e.id)).length}</td><td>${c.events_with_results}</td><td>${c.singles}</td><td>${c.doubles}</td></tr>`;
 });
 const rows=page.rows.map(e=>{const c=coverageRecord(e),d=deferred.get(e.id);
  const status=c?`${c.scope==='available_results'?esc(t('availableThrough'))+' '+datefmt(c.snapshot_date):esc(t('checked'))} · ${c.issues||0} ${esc(t('sourceIssues'))}${c.categories_discovered?`<div>${c.categories_visited??c.categories_selected}/${c.categories_discovered} ${esc(t(c.categories_visited===undefined?'phaseCategories':'categoryViews'))}</div>`:''}`:esc(e.source_status==='legacy_not_in_current_catalog'?t('legacy'):d?t(d.reason==='undated'?'undated':d.reason==='not_started_by_cutoff'?'notStarted':'notFinished'):t('pending'));
  return `<tr><td>${link('#event/'+encodeURIComponent(e.id),e.name)}<div>${esc(e.season)} · ${esc((c?.phases||[]).map(p=>t(p)).join(', '))}</div></td><td>${c?.singles||0}</td><td>${c?.doubles||0}</td><td>${c?.fixtures||0}</td><td>${status}</td></tr>`;
 });
 return `<div class="white-panel" style="margin-top:24px"><h3>${esc(t('coverage'))}</h3>
 <p>${coverage.event_catalog.count||0} ${esc(t('events'))} · ${esc((coverage.event_catalog.seasons||[]).join(', '))}</p>
 ${batch?`<p>${batch.attempted}/${batch.eligible} ${el?'πρόσθετες διοργανώσεις ελέγχθηκαν':'additional competitions checked'} · ${batch.pending} ${esc(t('pending'))} · ${batch.deferred.length} ${esc(t('deferred'))}. ${datefmt(batch.as_of)}</p>`:''}
 <p>${el?'Ο έλεγχος των δημόσιων σελίδων δεν αποδεικνύει πλήρες ιστορικό. Ορισμένες διοργανώσεις δεν έχουν αξιοποιήσιμα αποτελέσματα.':'Checking public pages does not establish complete history. Some competitions have no usable results.'}</p>
 <div class="link-row"><a class="text-link" href="coverage.json" download>${esc(t('coverageReport'))} (JSON)</a><a class="text-link" href="provenance.json" download>${esc(t('provenanceReport'))} (JSON)</a></div>
 ${dataTable(['season','checked','deferred','withResults','results','doubles'],summary)}
 <p>${el?'Στιγμιότυπα κατάταξης':'Ranking snapshots'}: ${(coverage.rankings||[]).map(r=>`${esc(r.category)} · ${datefmt(r.date)} (${r.rows})`).join('; ')}</p>
 <div class="filters"><label for="season-filter">${esc(t('season'))}</label><select id="season-filter" class="control"><option value="all">${esc(t('allSeasons'))}</option>${seasons.map(v=>`<option value="${esc(v)}" ${v===state.season?'selected':''}>${esc(v)}</option>`).join('')}</select><label class="sr-only" for="search-events">${esc(t('search'))}</label><input id="search-events" type="search" class="control" value="${esc(state.query)}" placeholder="${esc(t('search'))}"></div>
 ${dataTable(['events','results','doubles','fixtures','status'],rows)}${page.controls}</div>`;
}
function aboutPage(){return `<main class="container main">${crumb([['home',t('home')],['about',t('about')]])}<div class="paneltop"><div><span class="kicker">${esc(t('openData'))}</span><h2>${esc(t('dataTransparency'))}</h2></div></div><div class="info-grid" style="margin-top:0"><div class="white-panel"><h3>${esc(t('dataTransparency'))}</h3><p>${esc(t('dataTransparencyText'))}</p><p>${esc(t('statsNotComplete'))}</p><div class="link-row">${external('https://app.ttscore.io/customer/24',t('viewSource'))}</div></div><div class="white-panel"><h3>${esc(t('importStatus'))}</h3><div class="progress"><span>${db.events.length} ${esc(t('events'))}</span><span>${db.players.length} ${esc(t('players'))}</span><span>${totalSingles()} ${esc(t('results'))}</span><span>${totalDoubles()} ${esc(t('doubles'))}</span><span>${db.rankings.length} ${esc(t('rankings'))}</span></div><p style="margin-top:20px">${esc(t('coverage'))} · ${esc((db.meta.dataset_sha256||'').slice(0,16))}</p></div><div class="white-panel"><h3>${esc(t('architecture'))}</h3><p>${esc(t('architectureText'))}</p><p>${esc(t('openData'))}</p></div><div class="white-panel"><h3>${esc(t('importPlan'))}</h3><p>${esc(t('importPlanText'))}</p><p class="source-note">CSV → Python validation → static HTML → GitHub Pages.</p></div></div>${coverageDetails()}${db.meta.partitions?`<p class="source-note"><a class="text-link" href="offline.html" download>${state.lang==='el'?'Λήψη πλήρους αρχείου για χρήση χωρίς σύνδεση':'Download complete archive for offline use'} (HTML)</a></p>`:''}</main>`;}
function notFound(){return `<main class="container main">${crumb([['home',t('home')],['home','404']])}${empty('tableEmpty')}<a href="#home" class="text-link">${esc(t('goBack'))}</a></main>`;}
const EVENT_KINDS=['individual','team_league','team_cup','unchecked'],TEAM_KINDS=['team_league','team_cup'];
const kindCache=new Map();
// Type comes from the source navigation recorded at import, never from event names.
// Order matters: team cups and play-offs also expose knockout views.
function eventKind(e){
 if(!e||!e.id)return 'unchecked';
 if(kindCache.has(e.id))return kindCache.get(e.id);
 const c=db.meta.provenance?.coverage||{},id=e.id.replace(/^ttscore-/,''),phases=c.events?.[id]?.phases||[];
 const kind=c.team_tournaments?.[id]?'team_cup'
  :phases.includes('league')||c.leagues?.[id]||e.type==='league'?'team_league'
  :phases.some(p=>['groups','knockout','consolation'].includes(p))||e.type==='open'?'individual'
  :e.type==='cup'?'team_cup':'unchecked';
 kindCache.set(e.id,kind);return kind;
}
const kindTag=e=>{const k=eventKind(e);return `<span class="tag kind-${k}">${esc(t('kind_'+k))}</span>`;};
const kindIcon={individual:'●',team_league:'▦',team_cup:'◆',unchecked:'○'};
const initials=name=>String(name||'?').split(/[\s/.-]+/).filter(Boolean).slice(0,2).map(w=>w.charAt(0)).join('').toUpperCase()||'?';
const regNo=id=>/^httf-\d+$/.test(id||'')?`${t('regNo')} ${id.slice(5)}`:'';
function eventPlayers(id){const counts=db.meta.event_player_counts;if(counts)return counts[id]||0;return new Set((matchesByEvent.get(id)||[]).filter(m=>m.status==='completed').flatMap(m=>[m.player1_id,m.player2_id])).size;}
// Hosted list pages load no result files, so they read build-time totals.
function playerTotals(id){const s=db.meta.player_summary;if(s){const v=s[id]||[0,0];return {played:v[0],won:v[1]};}const ms=completedForPlayer(id);return {played:ms.length,won:ms.filter(m=>m.winner_id===id).length};}
let rankIndexCache=null;
function rankingIndex(){
 if(rankIndexCache)return rankIndexCache;
 const latestDate=new Map();for(const r of db.rankings){const d=latestDate.get(r.category);if(!d||d<r.date)latestDate.set(r.category,r.date);}
 const byPlayer=new Map();for(const r of db.rankings){if(r.date!==latestDate.get(r.category))continue;if(!byPlayer.has(r.player_id))byPlayer.set(r.player_id,[]);byPlayer.get(r.player_id).push(r);}
 return rankIndexCache={latestDate,byPlayer,cats:[...latestDate.keys()].sort((a,b)=>a.localeCompare(b,'el'))};
}
function sectionSwitch(active){return `<div class="seg" role="navigation">${['events','players'].map(k=>`<a class="seg-btn ${active===k?'active':''}" href="#${k}" ${active===k?'aria-current="page"':''}>${esc(t(k))}</a>`).join('')}</div>`;}
function eventRow(e){
 const n=completedByEvent.get(e.id)||0,k=eventKind(e);
 const dates=e.start_date&&e.end_date&&e.start_date!==e.end_date?`${datefmt(e.start_date)} – ${datefmt(e.end_date)}`:datefmt(e.start_date||e.end_date);
 return `<a class="event-row" href="#event/${encodeURIComponent(e.id)}"><div class="event-badge kind-${k}" aria-hidden="true"><b>${kindIcon[k]}</b><span>${esc(e.season||'')}</span></div><div class="event-row-main"><div class="event-row-date">◷ ${dates}</div><h3>${eventName(e)}</h3><div class="event-row-meta">${kindTag(e)}${e.region?`<span class="ellipsis">⌖ ${esc(e.region)}</span>`:''}</div><div class="event-row-stats">${n?`<span>⚔ ${n} ${esc(t('matchesShort'))}</span><span>👥 ${eventPlayers(e.id)} ${esc(t('playersShort'))}</span>`:`<span class="smallmuted">${esc(t(k==='unchecked'?'pending':'noResultsYet'))}</span>`}</div></div><span class="event-row-go" aria-hidden="true">›</span></a>`;
}
function eventSummary(ms){
 const rows=new Map();
 for(const m of ms){if(m.status!=='completed')continue;
  // Club comes from the match sheet: profile clubs are dated ranking observations.
  for(const [pid,club] of [[m.player1_id,m.club1_id],[m.player2_id,m.club2_id]]){const r=rows.get(pid)||{id:pid,club:'',played:0,won:0};r.played++;if(m.winner_id===pid)r.won++;if(club)r.club=club;rows.set(pid,r);}}
 return [...rows.values()].sort((a,b)=>b.won-a.won||(a.played-a.won)-(b.played-b.won)||getPlayer(a.id).name.localeCompare(getPlayer(b.id).name,'el'));
}
function eventPlayerRow(r){const p=getPlayer(r.id);return `<div class="player-row"><div class="avatar">${esc(initials(p.name))}</div><div class="player-row-main"><div class="smalltext">${esc(regNo(r.id))}</div>${link('#player/'+encodeURIComponent(r.id),p.name,'listname')}<div class="listmeta">${esc(r.club?getClub(r.club).name:'')}</div></div><div class="wl"><span>⚔ ${r.played} ${esc(t('matchesShort'))}</span><span class="won">✓ ${r.won}</span><span class="lost">✕ ${r.played-r.won}</span></div><button type="button" class="ghost-btn small" data-event-player="${esc(r.id)}">${esc(t('showMatches'))} →</button></div>`;}
function matchCard(m){
 const done=m.status==='completed',flip=done&&m.winner_id===m.player2_id;
 const [a,b]=flip?[m.player2_id,m.player1_id]:[m.player1_id,m.player2_id],[ca,cb]=flip?[m.club2_id,m.club1_id]:[m.club1_id,m.club2_id];
 const sa=flip?m.score2:m.score1,sb=flip?m.score1:m.score2;
 const score=[sa,sb].every(v=>v!==null&&v!==undefined&&v!=='')?`${sa}–${sb}`:'—';
 const games=(m.games||[]).map(g=>(flip?[g[1],g[0]]:g).join('–')).join(', ');
 const side=(pid,club,win,right)=>`<div class="mc-side ${right?'right':''}"><div class="avatar ${win?'win':''}">${esc(initials(getPlayer(pid).name))}</div><div class="mc-name"><div class="smalltext">${esc(regNo(pid))}</div>${link('#player/'+encodeURIComponent(pid),getPlayer(pid).name,'listname')}<div class="listmeta">${esc(club?getClub(club).name:'')}</div>${win?`<span class="winner">${esc(t('winner'))}</span>`:''}</div></div>`;
 return `<article class="match-card">${side(a,ca,done&&m.winner_id===a,false)}<div class="mc-mid"><div class="smalltext">${esc(t(m.phase||'league'))}${m.category?' · '+esc(m.category):''}</div><div class="mc-score">${esc(score)}</div>${games?`<div class="mc-games">${esc(games)}</div>`:''}<div class="smalltext">${datefmt(m.date)}${done?'':' · '+esc(t(m.status))}</div>${external(m.source_url,t('source'))}</div>${side(b,cb,false,true)}</article>`;
}
function playersPage(){
 const idx=rankingIndex(),cat=state.rosterCat;
 const sort=cat==='all'?(['played','name'].includes(state.rosterSort)?state.rosterSort:'played'):(['rank','played','name'].includes(state.rosterSort)?state.rosterSort:'rank');
 const rankIn=p=>(idx.byPlayer.get(p.id)||[]).find(r=>r.category===cat);
 let rows=db.players.filter(p=>searchHit(p,state.query));
 if(cat!=='all')rows=rows.filter(rankIn);
 const totals=new Map(rows.map(p=>[p.id,playerTotals(p.id)]));
 const byName=(a,b)=>a.name.localeCompare(b.name,'el');
 rows.sort(sort==='rank'?(a,b)=>rankIn(a).rank-rankIn(b).rank||byName(a,b):sort==='played'?(a,b)=>totals.get(b.id).played-totals.get(a.id).played||byName(a,b):byName);
 const page=paginate(rows),from=state.page*50;
 const sorts=(cat==='all'?['played','name']:['rank','played','name']).map(s=>`<option value="${s}" ${s===sort?'selected':''}>${esc(t('sort_'+s))}</option>`).join('');
 const list=page.rows.map(p=>{const tot=totals.get(p.id),r=cat==='all'?(idx.byPlayer.get(p.id)||[])[0]:rankIn(p);
  return `<a class="player-row" href="#player/${encodeURIComponent(p.id)}"><div class="rank-num">${r?'#'+r.rank:'—'}</div><div class="avatar">${esc(initials(p.name))}</div><div class="player-row-main"><div class="smalltext">${esc(regNo(p.id))}</div><div class="listname">${esc(p.name)}</div><div class="listmeta">${esc(getClub(p.club_id).name)}</div></div><div class="points">${r?`★ ${r.points==null?'—':esc(fmtPoints(r.points))}<div class="smalltext">${esc(r.category)} · ${datefmt(r.date)}</div>`:`<span class="smalltext">${esc(t('unranked'))}</span>`}</div><div class="wl">${tot.played?`<span>⚔ ${tot.played} ${esc(t('matchesShort'))}</span><span class="won">✓ ${tot.won}</span><span class="lost">✕ ${tot.played-tot.won}</span>`:`<span class="smalltext">${esc(t('noMatchesImported'))}</span>`}</div></a>`;}).join('');
 return `<main class="container main">${crumb([['home',t('home')],['players',t('players')]])}${sectionSwitch('players')}<div class="searchpanel"><div class="filters" style="margin:0"><label class="sr-only" for="search-roster">${esc(t('search'))}</label><input class="control" type="search" id="search-roster" placeholder="${esc(t('search'))}" value="${esc(state.query)}"><label class="sr-only" for="roster-category">${esc(t('category'))}</label><select id="roster-category" class="control"><option value="all">${esc(t('anyRanking'))}</option>${idx.cats.map(c=>`<option value="${esc(c)}" ${c===cat?'selected':''}>${esc(c)} · ${datefmt(idx.latestDate.get(c))}</option>`).join('')}</select><label class="sr-only" for="roster-sort">${esc(t('sortBy'))}</label><select id="roster-sort" class="control">${sorts}</select></div></div>${statusBox()}<div class="list-head"><span class="list-title">${esc(t('playerList'))}</span><span class="smallmuted">${rows.length?`${from+1}–${from+page.rows.length} / ${rows.length}`:''}</span></div>${list?`<div class="player-list">${list}</div>`:empty('noPlayers')}${page.controls}</main>`;
}
// USATT-style chart of official ranking snapshots. Only published dates are plotted:
// values are never carried forward or interpolated into months without a snapshot.
const fmtPoints=v=>new Intl.NumberFormat(state.lang==='el'?'el-GR':'en-US',{maximumFractionDigits:1}).format(Number(v));
const CHART_RANGES={all:0,'1y':12,'6m':6,'3m':3};
function niceTicks(lo,hi){
 if(lo===hi){const pad=Math.max(1,Math.abs(lo)*0.02);lo-=pad;hi+=pad;}
 const raw=(hi-lo)/5,mag=10**Math.floor(Math.log10(raw)),step=[1,2,2.5,5,10].map(k=>k*mag).find(s=>s>=raw);
 const first=Math.floor(lo/step)*step,last=Math.ceil(hi/step)*step,ticks=[];
 for(let v=first;v<=last+step/2;v+=step)ticks.push(Number(v.toFixed(6)));
 return {ticks,lo:first,hi:last};
}
function monthLabel(ms){const d=new Date(ms);const m=new Intl.DateTimeFormat(state.lang==='el'?'el-GR':'en-GB',{month:'short',timeZone:'UTC'}).format(d).replace('.','');return `${m}'${String(d.getUTCFullYear()).slice(2)}`;}
function monthTicks(t0,t1){
 const s=new Date(t0);let y=s.getUTCFullYear(),m=s.getUTCMonth()+(s.getUTCDate()>1?1:0);const months=[];
 for(let d=Date.UTC(y,m,1);d<=t1;d=Date.UTC(y,++m,1))months.push(d);
 const step=[1,2,3,6,12,24].find(k=>months.length/k<=7)||24;
 return months.filter((_,i)=>i%step===0);
}
function rankingChart(ranks){
 const cats=[...new Set(ranks.map(r=>r.category))].sort((a,b)=>a.localeCompare(b,'el'));
 const newest=[...ranks].sort((a,b)=>b.date.localeCompare(a.date))[0];
 const cat=cats.includes(state.chartCat)?state.chartCat:newest.category;
 const series=ranks.filter(r=>r.category===cat).sort((a,b)=>a.date.localeCompare(b.date));
 const byPoints=series.every(r=>r.points!==null&&r.points!==undefined&&r.points!=='');
 const value=r=>Number(byPoints?r.points:r.rank);
 const range=state.chartRange in CHART_RANGES?state.chartRange:'1y';
 const day=86400000,toMs=d=>Date.parse(d+'T00:00:00Z'),lastMs=toMs(series[series.length-1].date);
 let start=null;if(CHART_RANGES[range]){const d=new Date(lastMs);d.setUTCMonth(d.getUTCMonth()-CHART_RANGES[range]);start=d.getTime();}
 const rows=series.filter(r=>start===null||toMs(r.date)>=start);
 let t0=start??toMs(rows[0].date),t1=lastMs;if(t0===t1){t0-=15*day;t1+=15*day;}
 const y=niceTicks(Math.min(...rows.map(value)),Math.max(...rows.map(value)));
 const xPct=ms=>3+94*(ms-t0)/(t1-t0);
 // Points: higher is better. Rank fallback: position 1 sits at the top.
 const yPct=v=>6+88*(byPoints?(y.hi-v):(v-y.lo))/(y.hi-y.lo);
 const num=new Intl.NumberFormat(state.lang==='el'?'el-GR':'en-US',{maximumFractionDigits:1});
 const xt=monthTicks(t0,t1);
 const pts=rows.map(r=>{const i=series.indexOf(r),prev=series[i-1],delta=prev?value(r)-value(prev):null,x=xPct(toMs(r.date)),yy=yPct(value(r));
  const change=delta===null||delta===0?'':` (${delta>0?'+':'−'}${num.format(Math.abs(delta))})`;
  const label=`${datefmt(r.date)}: ${byPoints?num.format(value(r))+' '+t('points').toLowerCase()+' · ':''}#${r.rank} · ${r.category}${change}`;
  return {x,yy,html:`<span class="pt" tabindex="0" role="img" aria-label="${esc(label)}" style="left:${x.toFixed(2)}%;top:${yy.toFixed(2)}%"><span class="tip ${x>70?'tip-left':''} ${yy<28?'tip-below':''}">${datefmt(r.date)} : <b>${esc(byPoints?num.format(value(r)):'#'+r.rank)}</b>${esc(change)}<br>#${esc(r.rank)} · ${esc(r.category)}</span></span><i class="guide" style="top:${yy.toFixed(2)}%"></i>`};});
 const ranges=Object.keys(CHART_RANGES).map(k=>`<button type="button" id="range-${k}" class="${k===range?'active':''}" aria-pressed="${k===range}">${esc(t('range_'+k))}</button>`).join('');
 return `<div class="rchart"><div class="rchart-head"><h3>${esc(t(byPoints?'chartTitle':'chartTitleRank'))}</h3><div class="rchart-ranges" role="group">${ranges}</div></div>${cats.length>1?`<div class="filters"><label for="chart-category">${esc(t('category'))}</label><select id="chart-category" class="control">${cats.map(c=>`<option value="${esc(c)}" ${c===cat?'selected':''}>${esc(c)}</option>`).join('')}</select></div>`:''}<div class="rchart-body"><div class="rchart-ylabel">${esc(t(byPoints?'axisPoints':'axisRank'))}</div><div class="rchart-yaxis">${y.ticks.map(v=>`<span style="top:${yPct(v).toFixed(2)}%">${esc(byPoints?num.format(v):'#'+num.format(v))}</span>`).join('')}</div><div class="rchart-plot">${xt.map(ms=>`<i class="vgrid" style="left:${xPct(ms).toFixed(2)}%"></i>`).join('')}<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts.map(p=>`${p.x.toFixed(2)},${p.yy.toFixed(2)}`).join(' ')}" vector-effect="non-scaling-stroke"/></svg>${pts.map(p=>p.html).join('')}</div><div class="rchart-xaxis">${xt.map(ms=>`<span style="left:${xPct(ms).toFixed(2)}%">${esc(monthLabel(ms))}</span>`).join('')}</div></div><p class="source-note">${rows.length}/${series.length} ${esc(t('snapshotsShown'))} · ${esc(t('chartNote'))}</p></div>`;
}
function rankingSection(ranks){
 if(!ranks.length)return `<div class="section-header"><h3>${esc(t('rankHistory'))}</h3></div>${empty('noRankData')}`;
 return `<section class="white-panel rchart-panel">${rankingChart(ranks)}<details class="rtable"><summary>${esc(t('snapshots'))} · ${ranks.length}</summary>${dataTable(['date','category','rank','points','source'],ranks.map(r=>`<tr><td>${datefmt(r.date)}</td><td>${esc(r.category)}</td><td>#${r.rank}</td><td>${r.points==null?'—':esc(fmtPoints(r.points))}</td><td>${external(r.source_url,t('source'))}</td></tr>`))}</details></section>`;
}
function render(){document.documentElement.lang=state.lang;const route=hashRoute();if(prepareResults(route))return;const views={home:landing,events:eventsPage,players:playersPage,clubs:()=>rosterPage('clubs'),rankings:rankingsPage,h2h:h2hPage,about:aboutPage};const content=views[route.view]?views[route.view]():route.view==='event'?eventPage(route.id):route.view==='player'?playerPage(route.id):route.view==='club'?clubPage(route.id):notFound();app.innerHTML=header()+updateNotice()+content+footer();if(route.view==='h2h'){const a=document.getElementById('h2h-player1'),b=document.getElementById('h2h-player2');if(a)a.value=state.player1;if(b)b.value=state.player2;}}
window.addEventListener('hashchange',()=>{state.page=0;state.phaseFilter='all';state.query='';state.season='all';state.type='all';state.withResults=true;state.eventTab='';state.eventPlayer='';state.eventCategory='all';state.profileKind='all';state.rosterCat='all';state.rosterSort='';state.chartRange='1y';state.chartCat='';window.scrollTo({top:0,behavior:'auto'});render();});
function focusRerender(id){const el=document.getElementById(id);const start=el&&typeof el.selectionStart==='number'?el.selectionStart:undefined;render();const next=document.getElementById(id);if(next){next.focus();if(start!==undefined)next.setSelectionRange(start,start)}}
document.addEventListener('input',e=>{if(e.target.matches('#search-events,#search-roster')){state.page=0;state.query=e.target.value;focusRerender(e.target.id)}});
document.addEventListener('change',e=>{state.page=0;if(e.target.id==='phase-filter'){state.phaseFilter=e.target.value;render()}if(e.target.id==='ranking-date'){state.rankDate=e.target.value;render()}if(e.target.id==='season-filter'){state.season=e.target.value;render()}if(e.target.id==='type-filter'){state.type=e.target.value;render()}if(e.target.id==='results-only'){state.withResults=!!e.target.checked;render()}if(e.target.id==='event-category'){state.eventCategory=e.target.value;render()}if(e.target.id==='roster-category'){state.rosterCat=e.target.value;state.rosterSort='';render()}if(e.target.id==='roster-sort'){state.rosterSort=e.target.value;render()}if(e.target.id==='chart-category'){state.chartCat=e.target.value;render()}if(e.target.id==='ranking-category'){state.rankCategory=e.target.value;state.rankDate='latest';render()}if(e.target.id==='h2h-player1'){state.player1=e.target.value;render()}if(e.target.id==='h2h-player2'){state.player2=e.target.value;render()}});
document.addEventListener('click',e=>{if((e.target.closest('#archive-reload')||e.target.closest('#archive-update'))){location.reload();return;}if(e.target.closest('#page-prev')){state.page--;render()}for(const k of ['players','matches','doubles','fixtures'])if(e.target.closest('#tab-'+k)){state.eventTab=k;state.page=0;render();return;}for(const k of ['all','1y','6m','3m'])if(e.target.closest('#range-'+k)){state.chartRange=k;render();return;}for(const k of ['all','individual','team'])if(e.target.closest('#scope-'+k)){state.profileKind=k;state.page=0;render();return;}const kindChip=e.target.closest('[data-kind]');if(kindChip){state.type=kindChip.getAttribute('data-kind');state.page=0;render();return;}const pick=e.target.closest('[data-event-player]');if(pick){state.eventPlayer=pick.getAttribute('data-event-player');state.eventTab='matches';state.phaseFilter='all';state.page=0;render();window.scrollTo({top:0,behavior:'auto'});return;}if(e.target.closest('#page-next')){state.page++;render()}if(e.target.closest('#lang-switch')){state.lang=state.lang==='el'?'en':'el';try{localStorage.setItem('tt_lang',state.lang)}catch{}render()}});
render();
if(db.meta.partitions&&db.meta.release_id&&typeof setInterval==='function'){
 setInterval(checkForUpdate,5*60*1000);
 checkForUpdate();
}
})();
