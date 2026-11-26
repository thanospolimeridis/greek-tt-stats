(() => {
'use strict';
const db = JSON.parse(document.getElementById('site-data').textContent);
// Builds store ranking rows compactly (per-snapshot fields once); plain arrays also work.
function unpackRankings(value){
 if(Array.isArray(value))return value;
 if(!value||value.format!=='ranking-snapshots-v1')return null;
 const snapshots=value.snapshots.map(([date,category,source_id,source_url])=>({date,category,source_id,source_url}));
 // A row may end with its position in the category's previous list (0: not in it).
 return value.rows.map(([s,player_id,rank,points,club,previous_rank])=>({...snapshots[s],player_id,rank,points,club_id:value.clubs[club],...(previous_rank===undefined?{}:{previous_rank})}));
}
db.rankings=unpackRankings(db.rankings)||[];
db.standings=db.standings||[];
// Builds attach both players' official positions on the day of each match (see build.py).
function unpackMatchRanks(value){
 const map=new Map();
 if(!value||value.format!=='match-ranks-v1')return map;
 for(const [id,[d,c,first,second]] of Object.entries(value.rows))map.set(id,{date:value.dates[d],category:value.categories[c],first,second});
 return map;
}
db.matchRanks=unpackMatchRanks(db.match_ranks);
// Team-match counts per club from the build: {club id: [[event id, player id, played, won]]}.
db.clubPlayers=db.club_players||{};
const app = document.getElementById('app');
const dictionary = {
 el:{home:'Αρχική',events:'Διοργανώσεις',players:'Αθλητές',clubs:'Σωματεία',rankings:'Κατατάξεις',h2h:'Head to head',about:'Σχετικά',archive:'ΑΡΧΕΙΟ ΑΓΩΝΩΝ ΕΛΛΑΔΑΣ',heroTitle:'Η ιστορία του ελληνικού',heroHighlight:'πινγκ πονγκ.',heroCopy:'Διοργανώσεις, αγώνες, αθλητές και στατιστικά, σε ένα ενιαίο, ανοικτό αρχείο. Με τεκμηρίωση από τις πρωτογενείς πηγές.',seeEvents:'Εξερεύνηση διοργανώσεων',howItWorks:'Πώς λειτουργεί',sourceEvents:'Διοργανώσεις στο αρχείο',playersIndexed:'Αθλητές με δεδομένα',matchesVerified:'Επαληθευμένοι αγώνες',seasons:'Αγωνιστικές περίοδοι',verifiedSources:'Επαληθευμένες πηγές',dataPending:'Η πρώτη έκδοση περιλαμβάνει πραγματικές καταχωρίσεις διοργανώσεων από το TTScore. Τα αναλυτικά αποτελέσματα, οι αθλητές και οι κατατάξεις δεν έχουν εισαχθεί ακόμη· δεν εμφανίζουμε υποθετικά δεδομένα.',viewSource:'Δείτε στο TTScore',latestEvents:'Αρχείο διοργανώσεων',latestDesc:'Επιλεγμένες, επιβεβαιωμένες εγγραφές με σύνδεσμο στην επίσημη πηγή.',allEvents:'Όλες οι διοργανώσεις',noMatches:'Δεν υπάρχουν ακόμα εισαγμένοι και επαληθευμένοι αγώνες για αυτή τη διοργάνωση.',filterAll:'Όλοι οι τύποι',allSeasons:'Όλες οι περίοδοι',league:'Διασυλλογικό',open:'Open',cup:'Κύπελλο',finals:'Τελική φάση',search:'Αναζήτηση διοργάνωσης, αθλητή ή σωματείου...',date:'Ημερομηνία',region:'Περιοχή',type:'Τύπος',season:'Περίοδος',source:'Πηγή',results:'Αποτελέσματα',sourceRecord:'Πρωτότυπη εγγραφή',details:'Στοιχεία',name:'Όνομα',club:'Σωματείο',rank:'Θέση',points:'Βαθμοί',category:'Κατηγορία',opponent:'Αντίπαλος',score:'Σκορ',round:'Φάση',status:'Κατάσταση',playerHistory:'Ιστορικό αγώνων',rankHistory:'Ιστορικό κατάταξης',wins:'Νίκες',losses:'Ήττες',winRate:'Ποσοστό νικών',filter:'Φίλτρα',noPlayers:'Δεν έχουν εισαχθεί ακόμα εγγραφές αθλητών.',noClubs:'Δεν έχουν εισαχθεί ακόμα εγγραφές σωματείων.',noRankings:'Δεν έχουν εισαχθεί ακόμα επίσημα στιγμιότυπα κατατάξεων.',compare:'Σύγκριση αθλητών',noH2H:'Δεν υπάρχουν επαληθευμένοι μεταξύ τους αγώνες στη βάση.',selectTwo:'Επιλέξτε δύο διαφορετικούς αθλητές για τη σύγκριση.',missingPlayers:'Η σύγκριση θα ενεργοποιηθεί μετά την εισαγωγή ιστορικών αγώνων.',sourceOnly:'Στοιχεία διοργάνωσης',recorded:'Καταγεγραμμένοι αγώνες',fixtures:'Ομαδικές συναντήσεις',relatedPlayers:'Αθλητές διοργάνωσης',allPlayers:'Κατάλογος αθλητών',allClubs:'Κατάλογος σωματείων',tableEmpty:'Δεν υπάρχουν εγγραφές για αυτή την επιλογή.',overview:'Επισκόπηση',history:'Ιστορικό',view:'Προβολή',verified:'Πηγή επιβεβαιωμένη',statsNotComplete:'Τα στατιστικά αφορούν μόνο τους εισαγμένους αγώνες. Δεν είναι πλήρες ιστορικό καριέρας.',sourcePolicy:'Κάθε αποτέλεσμα διατηρεί τον σύνδεσμο της αρχικής πηγής και ελέγχεται πριν εμφανιστεί.',openData:'Ανοιχτός κώδικας · χωρίς συνδρομές',siteFooter:'Ανεξάρτητο έργο · Δεν αποτελεί επίσημη υπηρεσία της ΕΦΟΕπΑ.',dataTransparency:'Διαφάνεια δεδομένων',dataTransparencyText:'Οι διοργανώσεις καταχωρίζονται με αναφορά στις δημόσιες σελίδες του TTScore. Μέχρι να επαληθευθεί η εισαγωγή των αγώνων, οι αναλύσεις παραμένουν κενές. Οι μεταγενέστερες εισαγωγές ελέγχονται για μοναδικά αναγνωριστικά, βαθμολογίες και πηγές.',architecture:'Απλή αρχιτεκτονική',architectureText:'Στατικά αρχεία HTML και αποτελεσμάτων, Python για τις εισαγωγές και δημοσίευση μέσω GitHub Pages. Δεν απαιτούνται διακομιστής, εμπορική βάση δεδομένων ή εξωτερικές JavaScript βιβλιοθήκες.',importPlan:'Πώς προστίθενται αποτελέσματα',importPlanText:'Με εισαγωγή δομημένων αρχείων CSV (αθλητές, σωματεία, αγώνες, επίσημες κατατάξεις). Ο εισαγωγέας επικυρώνει τις αναφορές και δημιουργεί αυτόματα τον ιστότοπο. Η απευθείας σύνδεση TTScore απαιτεί επιβεβαίωση του τρόπου πρόσβασης.',dataPendingShort:'Σε αναμονή εισαγωγής',loadMore:'Περισσότερα',latestRecords:'Τελευταίες διοργανώσεις',clubFixtures:'Ομαδικές συναντήσεις',individualMatches:'Ατομικοί αγώνες',goBack:'Επιστροφή',noEvents:'Δεν βρέθηκαν διοργανώσεις.',fromSource:'Πηγή: TTScore / ΕΦΟΕπΑ',approx:'Εγγραφές αρχείου',eventsPresent:'Διοργανώσεις σε αυτό το δείγμα',noFixtures:'Δεν υπάρχουν εισαγμένες ομαδικές συναντήσεις.',noRankData:'Δεν υπάρχουν επίσημες κατατάξεις για τον αθλητή.',recordSource:'Προβολή πηγής',howMany:'αποτελέσματα',importStatus:'Κατάσταση κάλυψης'},
 en:{home:'Home',events:'Competitions',players:'Players',clubs:'Clubs',rankings:'Rankings',h2h:'Head to head',about:'About',archive:'GREEK TABLE TENNIS ARCHIVE',heroTitle:'The history of Greek',heroHighlight:'table tennis.',heroCopy:'Competitions, matches, athletes and statistics, all connected in one open, source-attributed archive.',seeEvents:'Explore competitions',howItWorks:'How it works',sourceEvents:'Catalogued competitions',playersIndexed:'Players with data',matchesVerified:'Verified matches',seasons:'Seasons represented',verifiedSources:'Source verified',dataPending:'The first release includes real event listings verified against TTScore. Detailed results, players and rankings have not yet been imported; no results or statistics are invented.',viewSource:'View on TTScore',latestEvents:'Competition archive',latestDesc:'Selected, verified competition listings linking directly to the source.',allEvents:'All competitions',noMatches:'No imported and verified matches for this event yet.',filterAll:'All types',allSeasons:'All seasons',league:'Team league',open:'Open',cup:'Cup',finals:'Finals',search:'Search competitions, players or clubs...',date:'Date',region:'Region',type:'Type',season:'Season',source:'Source',results:'Results',sourceRecord:'Original record',details:'Details',name:'Name',club:'Club',rank:'Rank',points:'Points',category:'Category',opponent:'Opponent',score:'Score',round:'Round',status:'Status',playerHistory:'Match history',rankHistory:'Ranking history',wins:'Wins',losses:'Losses',winRate:'Win percentage',filter:'Filters',noPlayers:'No player records have been imported yet.',noClubs:'No club records have been imported yet.',noRankings:'No official ranking snapshots have been imported yet.',compare:'Compare players',noH2H:'There are no verified matches between these players in this dataset.',selectTwo:'Select two distinct players to compare.',missingPlayers:'Comparison becomes available when historical match records have been imported.',sourceOnly:'Event metadata',recorded:'Recorded matches',fixtures:'Team fixtures',relatedPlayers:'Competition players',allPlayers:'Player directory',allClubs:'Club directory',tableEmpty:'There are no records matching this selection.',overview:'Overview',history:'History',view:'View',verified:'Source verified',statsNotComplete:'Statistics are based only on imported matches, not necessarily complete career histories.',sourcePolicy:'Every result retains a source link and is checked before publication.',openData:'Open-source · no subscriptions',siteFooter:'Independent project · Not an official service of the Greek federation.',dataTransparency:'Data transparency',dataTransparencyText:'Event listings are associated with their original public TTScore pages. Analytics stay empty until match ingestion is verified. Future imports validate stable identities, scores and source provenance.',architecture:'Simple architecture',architectureText:'Static HTML and result files, Python data imports and publication through GitHub Pages. No application server, commercial database or JavaScript libraries required.',importPlan:'Importing match results',importPlanText:'Structured CSV files for players, clubs, matches and official rankings feed the validator and static site builder. A direct TTScore connector depends on confirming the permitted access/export method.',dataPendingShort:'Awaiting import',loadMore:'Load more',latestRecords:'Latest competitions',clubFixtures:'Team fixtures',individualMatches:'Individual matches',goBack:'Back',noEvents:'No competitions match.',fromSource:'Source: TTScore / HTTF',approx:'Catalogued records',eventsPresent:'Competitions in this sample',noFixtures:'No imported team fixtures.',noRankData:'No official ranking data for this player.',recordSource:'View source',howMany:'results',importStatus:'Data coverage'}
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
Object.assign(dictionary.el,{kind_individual:"Ατομικό τουρνουά",kind_team_league:"Ομαδικό · βαθμολογία",kind_team_cup:"Ομαδικό · νοκ άουτ",kind_unchecked:"Δεν έχει ελεγχθεί ακόμη",onlyResults:"Μόνο με αποτελέσματα",matchesShort:"αγώνες",playersShort:"αθλητές",eventList:"Λίστα διοργανώσεων",noResultsYet:"Ελέγχθηκε· χωρίς αποτελέσματα απλού",matchesTab:"Αγώνες",winner:"Νικητής",played:"Αγώνες",eventsPlayed:"Συμμετοχές σε διοργανώσεις",bySeason:"Ανά αγωνιστική περίοδο",scope_all:"Όλες οι διοργανώσεις",scope_individual:"Ατομικά τουρνουά",scope_team:"Ομαδικές διοργανώσεις",regNo:"ΑΜ",showMatches:"Αγώνες",allCategories:"Όλες οι κατηγορίες",sortBy:"Ταξινόμηση",sort_rank:"Ταξινόμηση: θέση κατάταξης",sort_played:"Ταξινόμηση: περισσότεροι αγώνες",sort_name:"Ταξινόμηση: αλφαβητικά",anyRanking:"Όλοι οι αθλητές",move:"Μεταβολή",snapYear:"Έτος",snapMonth:"Μήνας",snapLatest:"Πιο πρόσφατη",playerList:"Λίστα αθλητών",unranked:"Χωρίς επίσημη κατάταξη",noMatchesImported:"Χωρίς εισαγμένους αγώνες",record:"Νίκες–Ήττες"});
Object.assign(dictionary.en,{kind_individual:"Individual tournament",kind_team_league:"Team · league table",kind_team_cup:"Team · knockout",kind_unchecked:"Not yet checked",onlyResults:"Only with results",matchesShort:"matches",playersShort:"players",eventList:"Competition list",noResultsYet:"Checked; no singles results",matchesTab:"Matches",winner:"Winner",played:"Played",eventsPlayed:"Competitions played",bySeason:"By season",scope_all:"All competitions",scope_individual:"Individual tournaments",scope_team:"Team competitions",regNo:"Reg.",showMatches:"Matches",allCategories:"All categories",sortBy:"Sort",sort_rank:"Sort: ranking position",sort_played:"Sort: most matches",sort_name:"Sort: name",anyRanking:"All players",move:"Change",snapYear:"Year",snapMonth:"Month",snapLatest:"Latest",playerList:"Player list",unranked:"No official ranking",noMatchesImported:"No imported matches",record:"Won–lost"});
Object.assign(dictionary.el,{chartTitle:"Βαθμοί κατάταξης στο χρόνο",chartTitleRank:"Θέση κατάταξης στο χρόνο",axisPoints:"Βαθμοί",axisRank:"Θέση",range_all:"Όλα",range_1y:"1Ε",range_6m:"6Μ",range_3m:"3Μ",snapshots:"Επίσημα στιγμιότυπα κατάταξης",snapshotsShown:"στιγμιότυπα στο διάστημα",chartNote:"Κάθε σημείο είναι μία δημοσιευμένη κατάταξη της ομοσπονδίας στο TTScore· δεν συμπληρώνονται ενδιάμεσοι μήνες."});
Object.assign(dictionary.en,{chartTitle:"Ranking points over time",chartTitleRank:"Ranking position over time",axisPoints:"Points",axisRank:"Position",range_all:"All",range_1y:"1Y",range_6m:"6M",range_3m:"3M",snapshots:"Official ranking snapshots",snapshotsShown:"snapshots in range",chartNote:"Each point is one published federation ranking on TTScore; months without a snapshot are not filled in."});
Object.assign(dictionary.el,{sharedPoints:"Ενιαίοι βαθμοί για όλες τις κατηγορίες του αθλητή"});
Object.assign(dictionary.en,{sharedPoints:"One points value across the player's categories"});
Object.assign(dictionary.el,{rankingHistoryReport:"Τεκμηρίωση ιστορικού κατατάξεων"});
Object.assign(dictionary.en,{rankingHistoryReport:"Ranking history provenance"});
Object.assign(dictionary.el,{searchAthlete:"Αναζήτηση αθλητή (όνομα ή ΑΜ)",rankingMatches:"εγγραφές κατάταξης για την αναζήτηση"});
Object.assign(dictionary.en,{searchAthlete:"Search athlete (name or reg. no.)",rankingMatches:"ranking entries match the search"});
Object.assign(dictionary.el,{topRanked:"Κορυφή της κατάταξης"});
Object.assign(dictionary.en,{topRanked:"Top of the rankings"});
Object.assign(dictionary.el,{inArchive:"Στο αρχείο",teamPlayers:"Αθλητές σε ομαδικούς αγώνες",clubNote:"Θέση, νίκες, ήττες, Disq και βαθμοί όπως τα δημοσιεύει το TTScore· οι ισόβαθμες ομάδες έχουν την ίδια θέση (=). «Στο αρχείο»: νίκες–ήττες στις συναντήσεις που έχουν εισαχθεί.",teamPlayersNote:"Ολοκληρωμένοι αγώνες απλού στις ομαδικές συναντήσεις του σωματείου που έχουν εισαχθεί."});
Object.assign(dictionary.en,{inArchive:"In archive",teamPlayers:"Players in team matches",clubNote:"Position, wins, losses, Disq and points as TTScore publishes them; teams level on points share a position (=). \"In archive\": won–lost in the fixtures that have been imported.",teamPlayersNote:"Completed singles in the club's imported team fixtures."});
Object.assign(dictionary.el,{insights:"Ανάλυση αγώνων",scoreLines:"Σκορ αγώνων",deciders:"Αγώνες που κρίθηκαν στο τελευταίο σετ",gamesRecord:"Σετ υπέρ–κατά",vsRanking:"Ανάλογα με τη θέση του αντιπάλου στην κατάταξη",oppHigher:"Αντίπαλος σε υψηλότερη θέση",oppLower:"Αντίπαλος σε χαμηλότερη θέση",oppLevel:"Αντίπαλος στην ίδια θέση",oppNone:"Χωρίς σύγκριση",vsRankingNote:"Θέσεις στην επίσημη κατάταξη που ίσχυε την ημέρα του αγώνα, δηλαδή στην πιο πρόσφατη δημοσιευμένη. «Χωρίς σύγκριση»: κάποιος από τους δύο δεν ήταν τότε στην ίδια κατάταξη.",bestWins:"Καλύτερες νίκες",bestWinsNote:"Νίκες απέναντι στους αντιπάλους με την υψηλότερη επίσημη θέση την ημέρα του αγώνα.",noRankedWins:"Καμία νίκη απέναντι σε αθλητή με επίσημη θέση την ημέρα του αγώνα.",topOpponents:"Συχνότεροι αντίπαλοι",opponentsShort:"αντίπαλοι"});
Object.assign(dictionary.en,{insights:"Match breakdown",scoreLines:"Score lines",deciders:"Matches that went to the final game",gamesRecord:"Games won–lost",vsRanking:"By the opponent's ranking position",oppHigher:"Opponent ranked higher",oppLower:"Opponent ranked lower",oppLevel:"Opponent in the same position",oppNone:"No comparison",vsRankingNote:"Positions in the official ranking in force on the match day, meaning the latest one published. \"No comparison\": one of the two was not in the same ranking list then.",bestWins:"Best wins",bestWinsNote:"Wins over the opponents who held the highest official position on the match day.",noRankedWins:"No wins over an opponent with an official position on the match day.",topOpponents:"Most-played opponents",opponentsShort:"opponents"});
Object.assign(dictionary.el,{standingsTab:"Βαθμολογία",team:"Ομάδα",disq:"Disq",teamsShort:"ομάδες",standingsReport:"Τεκμηρίωση βαθμολογιών",standingsNote:"Νίκες, ήττες, Disq και βαθμοί όπως τα δημοσιεύει το TTScore. Δεν υπολογίζονται από τις συναντήσεις του αρχείου και μπορεί να διαφέρουν από αυτές. Η πηγή δεν ορίζει σειρά στις ισοβαθμίες: οι ισόβαθμες ομάδες έχουν την ίδια θέση (=).",standingsEmpty:"Η πηγή δεν είχε δημοσιεύσει αποτελέσματα για αυτόν τον όμιλο.",retrieved:"Ανάκτηση από το TTScore",rankShort:"#",winsShort:"Ν",lossesShort:"Η",pointsShort:"Β"});
Object.assign(dictionary.en,{standingsTab:"Standings",team:"Team",disq:"Disq",teamsShort:"teams",standingsReport:"Standings provenance",standingsNote:"Wins, losses, Disq and points as TTScore publishes them. They are not calculated from the fixtures in this archive and can differ from them. The source gives no tie-break order, so teams level on points share a position (=).",standingsEmpty:"The source had published no results for this group.",retrieved:"Retrieved from TTScore",rankShort:"#",winsShort:"W",lossesShort:"L",pointsShort:"Pts"});
Object.assign(dictionary.el,{change:"Αλλαγή",nameOrReg:"όνομα ή ΑΜ",h2hHint:"Γράψτε όνομα ή αριθμό μητρώου και επιλέξτε αθλητή. Η διεύθυνση της σελίδας κρατά τη σύγκριση, ώστε να μπορείτε να τη μοιραστείτε.",h2hPickOther:"Επιλέξτε και τον δεύτερο αθλητή.",reportIssue:"Διόρθωση ή αφαίρεση στοιχείων",corrections:"Διορθώσεις και αφαίρεση στοιχείων",correctionsText:"Αν ένα αποτέλεσμα, ένα όνομα ή ένα σωματείο είναι λάθος, ή αν θέλετε να αφαιρεθούν στοιχεία που σας αφορούν, στείλτε αναφορά. Οι διορθώσεις τεκμηριώνονται και τα αιτήματα αφαίρεσης γίνονται σεβαστά.",correctionsPublic:"Η αναφορά είναι δημόσια στο GitHub: μη γράφετε περισσότερα προσωπικά στοιχεία από όσα χρειάζονται.",identityFixes:"ελεγμένες διορθώσεις ταυτότητας, όπου η πηγή είχε καταγράψει τον ίδιο αθλητή ή το ίδιο σωματείο με δύο τρόπους",identityReport:"Διορθώσεις ταυτότητας",includesRecorded:"Περιλαμβάνει αγώνες που η πηγή κατέγραψε ως",noRegNo:"χωρίς αριθμό μητρώου",alsoWritten:"Στην πηγή και ως",homeTitle:"Ελληνική Επιτραπέζια Αντισφαίριση"});
Object.assign(dictionary.en,{change:"Change",nameOrReg:"name or reg. no.",h2hHint:"Type a name or registration number and pick an athlete. The page address keeps the comparison, so you can share it.",h2hPickOther:"Pick the second athlete as well.",reportIssue:"Correct or remove a record",corrections:"Corrections and removal",correctionsText:"If a result, a name or a club is wrong, or you want records about you removed, send a report. Corrections are documented and removal requests are honoured.",correctionsPublic:"Reports are public on GitHub: include no more personal detail than needed.",identityFixes:"reviewed identity corrections, where the source had recorded one athlete or one club in two ways",identityReport:"Identity corrections",includesRecorded:"Includes matches the source recorded as",noRegNo:"no registration number",alsoWritten:"Also written in the source as",homeTitle:"Greek table tennis results"});
Object.assign(dictionary.el,{freshResults:"Αποτελέσματα έως",freshChecked:"έλεγχος πηγής",freshRankings:"κατάταξη",refreshChecked:"διοργανώσεις σε εξέλιξη ή νέες ελέγχθηκαν στην τελευταία ανανέωση"});
Object.assign(dictionary.en,{freshResults:"Results through",freshChecked:"source checked",freshRankings:"ranking of",refreshChecked:"competitions in progress or new checked in the latest refresh"});
Object.assign(dictionary.el,{feedback:"Σχόλια",fbTitle:"Πώς να γίνει καλύτερο το αρχείο;",fbIntro:"Γράψτε τι λείπει, τι δεν δουλεύει ή τι σας δυσκόλεψε. Κάθε μήνυμα διαβάζεται.",fbTopic:"Θέμα",fbTopic_idea:"Ιδέα ή πρόταση",fbTopic_broken:"Κάτι δεν λειτουργεί",fbTopic_unclear:"Κάτι είναι δυσνόητο ή δύσκολο να βρεθεί",fbTopic_other:"Κάτι άλλο",fbMessage:"Το μήνυμά σας",fbEmail:"Email για απάντηση",fbOptional:"προαιρετικό",fbEmailNote:"Χρησιμοποιείται μόνο για απάντηση στο μήνυμά σας.",fbSend:"Αποστολή",fbSending:"Αποστολή…",fbCorrections:"Για λάθος αποτέλεσμα ή αίτημα αφαίρεσης στοιχείων:",fbEmpty:"Γράψτε ένα μήνυμα πριν από την αποστολή.",fbBadEmail:"Η διεύθυνση email δεν φαίνεται σωστή. Διορθώστε την ή αφήστε το πεδίο κενό.",fbFailed:"Το μήνυμα δεν στάλθηκε. Ελέγξτε τη σύνδεσή σας και δοκιμάστε ξανά· το κείμενό σας δεν χάθηκε.",fbThanks:"Ευχαριστούμε, το μήνυμα στάλθηκε.",fbThanksText:"Αν αφήσατε email, η απάντηση θα έρθει εκεί.",fbAgain:"Νέο μήνυμα",fbAbout:"Έχετε μια ιδέα για το αρχείο ή βρήκατε κάτι που δεν δουλεύει;",fbOpen:"Στείλτε σχόλια"});
Object.assign(dictionary.en,{feedback:"Feedback",fbTitle:"How can the archive be better?",fbIntro:"Say what is missing, what does not work or what was hard to find. Every message is read.",fbTopic:"Topic",fbTopic_idea:"Idea or suggestion",fbTopic_broken:"Something does not work",fbTopic_unclear:"Something is unclear or hard to find",fbTopic_other:"Something else",fbMessage:"Your message",fbEmail:"Email for a reply",fbOptional:"optional",fbEmailNote:"Used only to reply to your message.",fbSend:"Send feedback",fbSending:"Sending…",fbCorrections:"For a wrong result or a removal request:",fbEmpty:"Write a message before sending.",fbBadEmail:"The email address does not look right. Correct it or leave the field empty.",fbFailed:"The message was not sent. Check your connection and try again; your text is still here.",fbThanks:"Thank you, your message was sent.",fbThanksText:"If you left an email address, the reply will come there.",fbAgain:"Send another",fbAbout:"Have an idea for the archive, or found something that does not work?",fbOpen:"Send feedback"});
const state={phaseFilter:'all',lang:(()=>{try{return localStorage.getItem('tt_lang')==='en'?'en':'el'}catch{return 'el'}})(), query:'', season:'all',type:'all',rankCategory:'all',rankDate:'latest',page:0,h2hQuery1:'',h2hQuery2:'',detailTab:'matches',withResults:true,eventTab:'',eventPlayer:'',eventCategory:'all',profileKind:'all',clubSeason:'',rosterCat:'',rosterSort:'',rosterDate:'',chartRange:'all',chartCat:''};
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
// Reviewed identity corrections from the build: {merged-away id: kept id} per kind.
// Old links to a merged identity open the kept one; its page names what it includes.
const corrected=db.meta.identity_corrections||{};
const keptId=(kind,id)=>(corrected[kind]&&Object.prototype.hasOwnProperty.call(corrected[kind],id))?corrected[kind][id]:id;
const mergedInto=(kind,id)=>Object.keys(corrected[kind]||{}).filter(k=>corrected[kind][k]===id).sort();
const REPORT_URL='https://github.com/thanospolimeridis/greek-tt-stats/issues/new';
const SITE_TITLE='Greek TT Archive';
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
let activePart=null,pendingPart=null,loadVersion=0,loadError=false,updateAvailable=false,newerVersion='';
// The release this page was built from (VERSION, changed only by scripts/release.py),
// linked from the footer to the list of what each release changed.
const CHANGELOG_URL='https://github.com/thanospolimeridis/greek-tt-stats/blob/main/CHANGELOG.md';
const versionTag=()=>db.meta.version?` · ${external(CHANGELOG_URL,'v'+db.meta.version)}`:'';
function updateNotice(){
 if(!updateAvailable)return '';
 const el=state.lang==='el';
 const text=newerVersion?(el?`Η έκδοση ${newerVersion} του αρχείου είναι διαθέσιμη.`:`Version ${newerVersion} of the archive is available.`):(el?'Υπάρχουν νεότερα δεδομένα στο αρχείο.':'An updated archive is available.');
 return `<div class="container"><div class="statusbox" role="status"><span>${esc(text)}</span><button class="ghost-btn small" id="archive-update">${el?'Φόρτωση νέας έκδοσης':'Load update'}</button></div></div>`;
}
async function checkForUpdate(){
 if(updateAvailable)return;
 try{
  const response=await fetch('version.json',{cache:'no-store'});
  if(!response.ok)return;
  const version=await response.json();
  if(typeof version.release_id==='string'&&version.release_id!==db.meta.release_id){
   updateAvailable=true;
   // Named only when the number changed too: a rebuilt copy of the same release has a new id.
   if(typeof version.version==='string'&&version.version!==db.meta.version)newerVersion=version.version;
   // Do not interrupt a search or an open filter while announcing new data.
   if(!document.activeElement?.matches('input,select,textarea'))render();
  }
 }catch{/* A failed update check must not interrupt the current archive. */}
}
function useResults(payload){
 for(const kind of ['matches','doubles','fixtures'])db[kind]=payload[kind];
 db.rankingRows=payload.rankings===undefined?null:unpackRankings(payload.rankings);
 db.standings=payload.standings||[];
 db.matchRanks=unpackMatchRanks(payload.match_ranks);
 db.clubPlayers=payload.club_players||{};
 indexResults();
}
function prepareResults(route){
 const parts=db.meta.partitions;if(!parts)return false;
 const kind=route.view==='h2h'?'player':route.view==='rankings'||route.view==='players'?'ranking':route.view;
 // The Athletes page needs a file only for a past snapshot; the latest one is inline.
 const id=route.view==='h2h'?h2hIds(route).find(Boolean)||'':route.view==='rankings'?(state.rankDate==='latest'?'':state.rankDate):route.view==='players'?state.rosterDate:route.id;
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
function hashRoute(){let hash;try{hash=decodeURIComponent(location.hash.replace(/^#\/?/,''))}catch{return {view:'404',id:''}};const [view, ...parts]=(hash||'home').split('/');const id=parts.join('/');return{view: view||'home', id:view==='player'?keptId('players',id):view==='club'?keptId('clubs',id):id};}
// Head to head keeps both athletes in the address, so a comparison can be linked: #h2h/<first>/<second>.
// A dash stands for a side that is not chosen yet.
function h2hIds(route=hashRoute()){if(route.view!=='h2h')return ['',''];const [a='',b='']=route.id.split('/');return [a,b].map(id=>id&&id!=='-'&&playerById.has(keptId('players',id))?keptId('players',id):'');}
const h2hHref=(a,b)=>'#h2h'+(a||b?'/'+(a?encodeURIComponent(a):'-')+(b?'/'+encodeURIComponent(b):''):'');
function navActive(name){const r=hashRoute();return r.view===name||(name==='events'&&r.view==='event')||(name==='players'&&r.view==='player')||(name==='clubs'&&r.view==='club')?'active':'';}
// Brand mark: a bat and ball, coloured from the stylesheet tokens.
const LOGO=`<svg viewBox="0 0 24 24" aria-hidden="true"><rect class="logo-handle" x="14.9" y="12.2" width="3.4" height="8.4" rx="1.6" transform="rotate(-45 16.6 16.4)"/><circle class="logo-blade" cx="10.4" cy="10.2" r="6.6"/><circle class="logo-ball" cx="19.4" cy="5.4" r="2.2"/></svg>`;
function header(){const items=['home','events','players','clubs','rankings','h2h'];return `<header class="topbar"><div class="container top-inner"><a href="#home" class="brand" aria-label="Greek TT Archive"><span class="brandmark">${LOGO}</span><span><span class="brandtitle">GREEK TT <span>ARCHIVE</span></span><span class="brandunder">ΕΠΙΤΡΑΠΕΖΙΑ ΑΝΤΙΣΦΑΙΡΙΣΗ</span></span></a><nav class="nav" aria-label="Main navigation">${items.map((k,i)=>`<a href="#${k}" class="navlink ${navActive(k)} ${i===1?'navmobile':''}">${esc(t(k))}</a>`).join('')}<button id="lang-switch" class="lang" aria-label="Switch language">${state.lang==='el'?'EN':'ΕΛ'}</button></nav></div></header>`;}
function footer(){return `<footer class="footer"><div class="container footer-inner"><div><strong>Greek TT Archive</strong><p>${esc(t('siteFooter'))}</p></div><div><div class="footer-code">${esc(t('openData'))}${versionTag()}</div><p>${external('https://app.ttscore.io/customer/24','TTScore')} · ${link('#about',t('dataTransparency'))} · ${external(REPORT_URL,t('reportIssue'))}${feedbackOn()?' · '+link('#feedback',t('feedback')):''}</p></div></div></footer>`;}
// Home search: a few athletes, competitions and clubs for the typed text, each a link.
// A number alone is also tried as a federation registration number.
function homeSearch(){
 const q=state.query.trim();if(!q)return '';
 const hits=(list,n)=>list.filter(v=>searchHit(v,q)).slice(0,n);
 const byReg=/^\d+$/.test(q)?playerById.get('httf-'+q):null;
 const players=[...(byReg?[byReg]:[]),...hits(db.players,6).filter(p=>p!==byReg)].slice(0,6);
 const hit=(href,name,meta)=>`<a class="search-hit" href="${esc(href)}"><span class="listname">${esc(name)}</span><span class="listmeta">${esc(meta)}</span></a>`;
 const group=(key,rows)=>rows.length?`<div class="search-group">${esc(t(key))}</div>${rows.join('')}`:'';
 const body=group('players',players.map(p=>hit('#player/'+encodeURIComponent(p.id),p.name,clubLine(p.club_id,p.id))))
  +group('events',hits(db.events,5).map(e=>hit('#event/'+encodeURIComponent(e.id),e.name,[t('kind_'+eventKind(e)),e.season].filter(Boolean).join(' · '))))
  +group('clubs',hits(db.clubs,4).map(c=>hit('#club/'+encodeURIComponent(c.id),c.name,c.region||'')));
 return `<div class="searchresults" role="region" aria-label="${esc(t('results'))}">${body||`<p class="search-none">${esc(t('tableEmpty'))}</p>`}</div>`;
}
function hero(){
 const quick=[['events','events'],['players','players'],['clubs','clubs'],['rankings','rankings'],['about','howItWorks']];
 return `<section class="hero"><div class="container heroinner"><div class="herocopy"><div class="eyebrow"><span class="tiny-dot"></span>${esc(t('archive'))}</div><h1>${esc(t('heroTitle'))} <strong>${esc(t('heroHighlight'))}</strong></h1><p>${esc(t('heroCopy'))}</p></div><div class="hero-search" role="search"><label class="sr-only" for="search-home">${esc(t('search'))}</label><input class="control" type="search" id="search-home" autocomplete="off" placeholder="${esc(t('search'))}" value="${esc(state.query)}">${homeSearch()}</div><div class="heroact">${quick.map(([href,key])=>`<a class="light-btn" href="#${href}">${esc(t(key))}</a>`).join('')}</div>${statsBand()}${freshness()}</div></section>`;
}
// How fresh the archive is: the newest result, the last check of the source and the ranking in force.
function freshness(){const d=db.meta.data_through||{};const parts=[['results','freshResults'],['checked','freshChecked'],['rankings','freshRankings']].filter(([k])=>d[k]).map(([k,label])=>`${esc(t(label))} ${datefmt(d[k])}`);return parts.length?`<p class="fresh-note">${parts.join(' · ')}</p>`:'';}
function statsBand(){const values=[[db.events.length,'sourceEvents'],[db.players.length,'playersIndexed'],[totalSingles(),'matchesVerified'],[seasons.length,'seasons']];return `<section class="stats-band" aria-label="Archive coverage">${values.map(([v,k])=>`<div class="stat"><div class="statnum">${v.toLocaleString(state.lang==='el'?'el-GR':'en-US')}</div><div class="statlabel">${esc(t(k))}</div></div>`).join('')}</section>`;}
// Shown only when there is nothing to list. The reminder that statistics cover imported matches
// alone stays in the page notes and on About, not in a box on every page.
function statusBox(message){const key=message||(totalSingles()?'statsNotComplete':'dataPending');if(key==='statsNotComplete')return '';return `<div class="statusbox" role="status"><span class="circle">ⓘ</span><div><strong>${esc(t('coverage'))}:</strong> ${esc(t(key))}</div></div>`;}
function paginate(rows){const size=50;const pages=Math.max(1,Math.ceil(rows.length/size));state.page=Math.max(0,Math.min(state.page,pages-1));return {rows:rows.slice(state.page*size,(state.page+1)*size),controls:pages>1?`<div class="filters"><button class="ghost-btn small" id="page-prev" ${state.page===0?'disabled':''}>${esc(t('previous'))}</button><span>${state.page+1} / ${pages} · ${rows.length}</span><button class="ghost-btn small" id="page-next" ${state.page===pages-1?'disabled':''}>${esc(t('next'))}</button></div>`:''};}
function filteredEvents(kind=state.type){return db.events.filter(e=>(state.season==='all'||e.season===state.season)&&(kind==='all'||eventKind(e)===kind)&&(!state.withResults||(completedByEvent.get(e.id)||0)>0)&&searchHit(e,state.query));}
function eventFilters(){const kinds=['all',...EVENT_KINDS];return `<div class="searchpanel"><div class="filters" style="margin:0"><label class="sr-only" for="search-events">${esc(t('search'))}</label><input class="control" type="search" id="search-events" placeholder="${esc(t('search'))}" value="${esc(state.query)}"><label class="sr-only" for="season-filter">${esc(t('season'))}</label><select class="control" id="season-filter"><option value="all">${esc(t('allSeasons'))}</option>${seasons.map(s=>`<option value="${esc(s)}" ${s===state.season?'selected':''}>${esc(s)}</option>`).join('')}</select><label class="checkline"><input type="checkbox" id="results-only" ${state.withResults?'checked':''}> ${esc(t('onlyResults'))}</label></div><div class="kind-chips" role="group" aria-label="${esc(t('type'))}">${kinds.map(k=>`<button type="button" class="chip ${state.type===k?'active':''}" data-kind="${k}" aria-pressed="${state.type===k}">${k==='all'?esc(t('filterAll')):`<i class="dot kind-${k}"></i>${esc(t('kind_'+k))}`} · ${filteredEvents(k).length}</button>`).join('')}</div></div>`;}
function eventsSection(){const rows=filteredEvents(),page=paginate(rows),from=state.page*50;return `<div class="list-head"><span class="list-title">${esc(t('eventList'))}</span><span class="smallmuted">${rows.length?`${from+1}–${from+page.rows.length} / ${rows.length}`:''}</span></div>`+(page.rows.length?`<div class="event-list">${page.rows.map(eventRow).join('')}</div>${page.controls}`:empty('noEvents'));}
function empty(k,icon='◌'){return `<div class="empty"><div class="empty-icon" aria-hidden="true">${icon}</div><h3>${esc(t('dataPendingShort'))}</h3><p>${esc(t(k))}</p><a class="ghost-btn small" href="#about">${esc(t('howItWorks'))} →</a></div>`;}
// Home panel: the first five of the two senior lists in the latest official ranking.
function homeRankings(){
 const idx=rankingIndex(),cats=idx.cats.slice(0,2);if(!cats.length)return '';
 const groups=cats.map(cat=>{const date=idx.latestDate.get(cat);
  const rows=db.rankings.filter(r=>r.category===cat&&r.date===date).sort((a,b)=>a.rank-b.rank).slice(0,5);
  return `<div class="rank-group"><div class="rank-group-head"><strong>${esc(cat)}</strong><span class="smalltext">${datefmt(date)}</span></div>${rows.map(r=>`<a class="rank-row" href="#player/${encodeURIComponent(r.player_id)}"><span class="rank-num">${esc(r.rank)}</span><span class="listname ellipsis">${esc(getPlayer(r.player_id).name)}</span><span class="rank-points">${r.points==null?'—':esc(fmtPoints(r.points))}</span></a>`).join('')}</div>`;}).join('');
 return `<section class="white-panel home-ranks"><div class="section-header"><h3>${esc(t('topRanked'))}</h3><a class="text-link" href="#rankings">${esc(t('rankings'))} →</a></div>${groups}</section>`;
}
// The home list leads with competitions that already have results, newest first.
function landing(){const n=db.events.length,played=db.events.filter(e=>(completedByEvent.get(e.id)||0)>0),latest=(played.length?played:db.events).slice(0,8),ranks=homeRankings();return hero()+`<main class="container main">${statusBox()}<div class="home-grid ${ranks?'':'single'}"><section><div class="section-header"><h3>${esc(t('latestRecords'))}</h3><a class="text-link" href="#events">${esc(t('allEvents'))} →</a></div>${latest.length?`<div class="event-list">${latest.map(eventRow).join('')}</div>`:empty('noEvents')}<p class="source-note">${esc(t('latestDesc'))}</p></section>${ranks}</div><div class="info-grid"><section class="white-panel"><span class="kicker">${esc(t('dataTransparency'))}</span><h3>${esc(t('sourcePolicy'))}</h3><p>${esc(t('dataTransparencyText'))}</p><div class="link-row">${external('https://app.ttscore.io/customer/24',t('viewSource'))}</div></section><section class="white-panel"><span class="kicker">${esc(t('approx'))}</span><h3>${n} ${esc(t('eventsPresent'))}</h3><p>${esc(t('architectureText'))}</p><a href="#about" class="text-link">${esc(t('howItWorks'))} →</a></section></div></main>`;}
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
 return `<tr><td>${datefmt(m.date)}</td><td>${id?link('#player/'+encodeURIComponent(counterpart),getPlayer(counterpart).name):link('#player/'+encodeURIComponent(m.player1_id),getPlayer(m.player1_id).name)+' <span class="smalltext">vs</span> '+link('#player/'+encodeURIComponent(m.player2_id),getPlayer(m.player2_id).name)}</td><td><span class="score ${result?(result==='✓'?'win':'loss'):''}">${esc(result)} ${esc(score)}</span>${games?`<details><summary>${esc(t('games'))}</summary>${esc(games)}</details>`:''}<div class="smalltext">${esc(t(m.status))}</div></td><td>${link('#event/'+encodeURIComponent(m.event_id),getEvent(m.event_id).name)}<div class="smalltext">${esc(t(m.phase||'league'))} · ${esc(m.category||'')}</div></td><td>${external(m.source_url,t('source'))}</td></tr>`;
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
 const st=db.standings.filter(r=>r.event_id===id);
 const tabs=[['standings',st.length],['players',summary.length],['matches',all.length],['doubles',ds.length],['fixtures',fs.length]].filter(([key,n])=>n||key==='matches');
 const tab=tabs.some(([key])=>key===state.eventTab)?state.eventTab:st.length?'standings':summary.length?'players':'matches';
 const dates=e.start_date&&e.end_date&&e.start_date!==e.end_date?`${datefmt(e.start_date)} – ${datefmt(e.end_date)}`:datefmt(e.start_date||e.end_date);
 const catFilter=cats.length>1&&(tab==='players'||tab==='matches')?`<label for="event-category">${esc(t('category'))}</label><select id="event-category" class="control"><option value="all">${esc(t('allCategories'))}</option>${cats.map(c=>`<option value="${esc(c)}" ${c===state.eventCategory?'selected':''}>${esc(c)}</option>`).join('')}</select>`:'';
 let body='';
 if(tab==='standings')body=standingsTables(st);
 else if(tab==='players'){const page=paginate(summary);body=`${catFilter?`<div class="filters">${catFilter}</div>`:''}<div class="player-list is-event"><div class="list-cols" aria-hidden="true"><span></span><span>${esc(t('name'))}</span><span class="num">${esc(t('record'))}</span><span></span></div>${page.rows.map(eventPlayerRow).join('')}</div>${page.controls}`;}
 else if(tab==='matches'){
  const phases=[...new Set(all.map(m=>m.phase||'league'))];
  const ms=inCat.filter(m=>(state.phaseFilter==='all'||(m.phase||'league')===state.phaseFilter)&&(!state.eventPlayer||m.player1_id===state.eventPlayer||m.player2_id===state.eventPlayer));
  const page=paginate(ms);
  body=`<div class="filters">${phases.length>1||phases[0]!=='league'?`<label for="phase-filter">${esc(t('singlesPhase'))}</label><select id="phase-filter" class="control"><option value="all">${esc(t('allPhases'))}</option>${phases.map(p=>`<option value="${esc(p)}" ${p===state.phaseFilter?'selected':''}>${esc(t(p))}</option>`).join('')}</select>`:''}${catFilter}${state.eventPlayer?`<button type="button" class="chip active" data-event-player="">${esc(getPlayer(state.eventPlayer).name)} ✕</button>`:''}<span class="smallmuted">${ms.length} ${esc(t('matchesShort'))}</span></div>${page.rows.length?`<div class="match-list">${page.rows.map(matchEntry).join('')}</div>`:empty('noMatches')}${page.controls}`;
 }
 else if(tab==='doubles')body=doublesTable(ds);
 else body=fixturesTable(fs);
 return `<main class="container main">${crumb([['home',t('home')],['events',t('events')],['event/'+id,e.name]])}<div class="detailhead"><div class="detailhead-top"><div class="detail-title-area"><span class="kicker">${esc(t('kind_'+kind))} · ${esc(e.season)}</span><h1 class="title-detail">${eventName(e)}</h1><div class="detail-chips">${kindTag(e)}<span>◷ ${dates}</span><span>⌖ ${esc(e.region||'—')}</span></div><div class="proof">✓ ${esc(t(e.source_status==='legacy_not_in_current_catalog'?'legacy':'verified'))} · TTScore</div></div><div>${external(e.source_url,t('viewSource'))}</div></div></div><div class="results-grid"><div class="metric"><span>${esc(t('individualMatches'))}</span><strong>${completed.length}</strong></div><div class="metric"><span>${esc(t('players'))}</span><strong>${eventSummary(all).length}</strong></div><div class="metric"><span>${esc(t(fs.length?'clubFixtures':'doubles'))}</span><strong>${fs.length||ds.length}</strong></div></div><div class="subtabs" role="tablist">${tabs.map(([key,n])=>`<button type="button" role="tab" id="tab-${key}" class="subtab ${key===tab?'active':''}" aria-selected="${key===tab}">${esc(t(key==='standings'?'standingsTab':key==='players'?'players':key==='matches'?'matchesTab':key==='doubles'?'doubles':'clubFixtures'))} <span class="tabcount">${n}</span></button>`).join('')}</div>${body}${eventCoverageNote(e)}<p class="source-note" style="margin-top:22px">${esc(t('statsNotComplete'))} ${external(e.source_url,t('recordSource'))}</p></main>`;
}
// League tables are the source's own numbers. Position is only an order by its points:
// the source's "#" is a draw slot and it publishes no tie-break, so level teams share a place.
// Table headers; narrow screens swap long column names for the usual one-letter ones
// and hide columns marked optional. A column is a key or [key, optional].
function columnHeads(columns){return columns.map(c=>{const [k,optional]=[].concat(c),short=dictionary[state.lang][k+'Short'];return `<th scope="col"${optional?' class="opt"':''}>${short?`<span class="th-full">${esc(t(k))}</span><abbr class="th-short" title="${esc(t(k))}">${esc(short)}</abbr>`:esc(t(k))}</th>`;}).join('');}
function standingPlaces(group){
 const started=group.some(r=>r.wins||r.losses||r.disqualified||r.points);
 return new Map(group.map(r=>[r.id,started?1+group.filter(o=>o.points>r.points).length+(group.filter(o=>o.points===r.points).length>1?'=':''):'—']));
}
function standingsTables(rows){
 const head=columnHeads(['rank','team','wins','losses','disq','points']);
 const groups=new Map();
 for(const r of rows){if(!groups.has(r.group_id))groups.set(r.group_id,[]);groups.get(r.group_id).push(r);}
 return [...groups.values()].sort((a,b)=>a[0].category.localeCompare(b[0].category,'el')||a[0].group_id-b[0].group_id).map(g=>{
  const places=standingPlaces(g),started=places.get(g[0].id)!=='—';
  const body=[...g].sort((a,b)=>b.points-a.points||a.slot-b.slot).map(r=>{
   // The second source label is shown only when it says more than the club name
   // (not a cut-off copy or the same name with different punctuation).
   const bare=v=>v.replace(/[^\p{L}\p{N}]/gu,''),other=bare(r.club_name).startsWith(bare(r.team_name))?'':`<div class="smalltext">${esc(r.team_name)}</div>`;
   return `<tr><td><strong>${places.get(r.id)}</strong></td><td>${clubById.has(r.club_id)?link('#club/'+encodeURIComponent(r.club_id),r.club_name):esc(r.club_name)}${other}</td><td>${r.wins}</td><td>${r.losses}</td><td>${r.disqualified}</td><td><strong>${r.points}</strong></td></tr>`;});
  return `<section class="standings-group"><div class="section-header"><h3>${esc(g[0].category)}</h3><span class="smallmuted">${g.length} ${esc(t('teamsShort'))}</span></div><div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body.join('')}</tbody></table></div><p class="source-note">${started?'':esc(t('standingsEmpty'))+' '}${esc(t('retrieved'))}: ${datefmt(g[0].as_of)} · ${external(g[0].source_url,t('source'))}</p></section>`;
 }).join('')+`<p class="source-note">${esc(t('standingsNote'))}</p>`;
}
function rosterPage(kind){const isPlayer=kind==='players';const data=isPlayer?db.players:db.clubs;const title=isPlayer?t('allPlayers'):t('allClubs');const page=paginate(data.filter(v=>searchHit(v,state.query)).sort((a,b)=>a.name.localeCompare(b.name,'el')));const list=page.rows;return `<main class="container main">${crumb([['home',t('home')],[kind,t(kind)]])}<div class="paneltop"><div><span class="kicker">${esc(t('archive'))}</span><h2>${esc(title)}</h2></div></div>${statusBox()}<div class="filters"><label class="sr-only" for="search-roster">${esc(t('search'))}</label><input class="control" type="search" id="search-roster" placeholder="${esc(t('search'))}" value="${esc(state.query)}"></div>${list.length?`<div class="cards">${list.map(v=>`<a href="#${isPlayer?'player':'club'}/${encodeURIComponent(v.id)}" class="${isPlayer?'person-card':'club-card'}"><div class="listmain"><div class="round-icon">${esc((v.name||'?').charAt(0))}</div><div><div class="listname">${esc(v.name)}</div><div class="listmeta">${isPlayer?esc(getClub(v.club_id).name):esc(v.region||'')}</div></div></div></a>`).join('')}</div>`:empty(isPlayer?'noPlayers':'noClubs')}${page.controls}</main>`;}
// Profile breakdown of completed singles in the selected scope. Everything is a count of
// imported matches; ranking positions come from the build's join with official snapshots.
function playerInsights(done,id){
 const lines=new Map(),opponents=new Map(),vs={oppHigher:[0,0],oppLower:[0,0],oppLevel:[0,0],oppNone:[0,0]},beaten=[];
 let deciders=[0,0],games=[0,0],ranked=false;
 for(const m of done){
  const first=id===m.player1_id,won=m.winner_id===id,other=first?m.player2_id:m.player1_id;
  if([m.score1,m.score2].every(v=>v!==null&&v!==undefined&&v!=='')){
   const mine=Number(first?m.score1:m.score2),theirs=Number(first?m.score2:m.score1),key=mine+'–'+theirs;
   const line=lines.get(key)||{mine,theirs,count:0};line.count++;lines.set(key,line);
   games[0]+=mine;games[1]+=theirs;
   if(mine+theirs===(m.best_of||5))deciders[won?0:1]++;
  }
  const o=opponents.get(other)||{id:other,played:0,won:0};o.played++;if(won)o.won++;opponents.set(other,o);
  const c=db.matchRanks.get(m.id),mine=c?(first?c.first:c.second):null,theirs=c?(first?c.second:c.first):null;
  if(c)ranked=true;
  vs[mine!=null&&theirs!=null?(theirs<mine?'oppHigher':theirs>mine?'oppLower':'oppLevel'):'oppNone'][won?0:1]++;
  if(won&&theirs!=null)beaten.push({m,other,position:theirs,category:c.category,score:first?`${m.score1}–${m.score2}`:`${m.score2}–${m.score1}`});
 }
 const record=([w,l])=>`<span><b>${w}–${l}</b>${w+l?` <span class="smallmuted">${Math.round(w/(w+l)*100)}%</span>`:''}</span>`;
 const row=(label,value)=>`<div class="stat-row"><span>${label}</span>${value}</div>`;
 const scoreRows=[...lines.values()].sort((a,b)=>(b.mine>b.theirs)-(a.mine>a.theirs)||(a.mine>a.theirs?a.theirs-b.theirs:b.mine-a.mine)).map(l=>row(`<span class="${l.mine>l.theirs?'won':'lost'}">${l.mine>l.theirs?'✓':'✕'} ${l.mine}–${l.theirs}</span>`,`<b>${l.count}</b>`)).join('');
 const panels=[`<section class="white-panel"><h3>${esc(t('scoreLines'))}</h3>${scoreRows}${row(esc(t('deciders')),record(deciders))}${row(esc(t('gamesRecord')),`<b>${games[0]}–${games[1]}</b>`)}</section>`];
 if(ranked){
  panels.push(`<section class="white-panel"><h3>${esc(t('vsRanking'))}</h3>${Object.entries(vs).filter(([k,v])=>k!=='oppLevel'||v[0]+v[1]).map(([k,v])=>row(esc(t(k)),record(v))).join('')}<p class="source-note">${esc(t('vsRankingNote'))}</p></section>`);
  const best=beaten.sort((a,b)=>a.position-b.position||b.m.date.localeCompare(a.m.date)).slice(0,5);
  panels.push(`<section class="white-panel"><h3>${esc(t('bestWins'))}</h3>${best.length?best.map(b=>row(`<strong>#${b.position}</strong> <span class="smalltext">${esc(b.category)}</span> · ${link('#player/'+encodeURIComponent(b.other),getPlayer(b.other).name)}`,`<span class="smalltext">${esc(b.score)} · ${datefmt(b.m.date)}</span>`)).join('')+`<p class="source-note">${esc(t('bestWinsNote'))}</p>`:`<p class="source-note">${esc(t('noRankedWins'))}</p>`}</section>`);
 }
 const top=[...opponents.values()].sort((a,b)=>b.played-a.played||b.won-a.won||getPlayer(a.id).name.localeCompare(getPlayer(b.id).name,'el')).slice(0,6);
 panels.push(`<section class="white-panel"><h3>${esc(t('topOpponents'))}</h3>${top.map(o=>row(link('#player/'+encodeURIComponent(o.id),getPlayer(o.id).name),record([o.won,o.played-o.won]))).join('')}<p class="source-note">${opponents.size} ${esc(t('opponentsShort'))}</p></section>`);
 return `<div class="section-header"><h3>${esc(t('insights'))}</h3></div><div class="insight-grid">${panels.join('')}</div>`;
}
// Says which other source identities a corrected profile includes (see identity_corrections.py).
function mergedNote(id){const ids=mergedInto('players',id);return ids.length?`<div class="proof">${esc(t('includesRecorded'))} ${esc(ids.map(v=>regNo(v)||t('noRegNo')).join(', '))}</div>`:'';}
function playerPage(id){
 const p=playerById.get(id);if(!p)return notFound();
 const allMs=[...(matchesByPlayer.get(id)||[])].sort((a,b)=>b.date.localeCompare(a.date));
 const scopeOf=m=>{const k=eventKind(getEvent(m.event_id));return TEAM_KINDS.includes(k)?'team':k};
 const inScope=m=>state.profileKind==='all'||scopeOf(m)===state.profileKind;
 const ms=allMs.filter(inScope),done=ms.filter(m=>m.status==='completed');
 const wins=done.filter(m=>m.winner_id===id).length,losses=done.length-wins,rate=done.length?Math.round(wins/done.length*100):null;
 const scopeCount=k=>allMs.filter(m=>m.status==='completed'&&(k==='all'||scopeOf(m)===k)).length;
 const ranks=(db.rankingRows||db.rankings).filter(r=>r.player_id===id).sort((a,b)=>b.date.localeCompare(a.date));const latest=ranks[0];
 const bySeason=new Map(),byEvent=new Map();
 for(const m of done){const ev=getEvent(m.event_id),s=ev.season||'—';
  const row=bySeason.get(s)||{events:new Set(),played:0,won:0};row.events.add(m.event_id);row.played++;if(m.winner_id===id)row.won++;bySeason.set(s,row);
  const er=byEvent.get(m.event_id)||{ev,last:m.date,played:0,won:0};er.played++;if(m.winner_id===id)er.won++;if(m.date>er.last)er.last=m.date;byEvent.set(m.event_id,er);}
 const seasonRows=[...bySeason.entries()].sort((a,b)=>b[0].localeCompare(a[0])).map(([s,r])=>`<tr><td>${esc(s)}</td><td>${r.events.size}</td><td>${r.played}</td><td>${r.won}</td><td>${r.played-r.won}</td><td>${Math.round(r.won/r.played*100)}%</td></tr>`);
 const eventRows=[...byEvent.values()].sort((a,b)=>b.last.localeCompare(a.last)).map(r=>`<tr><td>${datefmt(r.last)}</td><td>${link('#event/'+encodeURIComponent(r.ev.id),r.ev.name)}<div class="smalltext">${esc(r.ev.season||'')}</div></td><td>${kindTag(r.ev)}</td><td>${r.played}</td><td><span class="score">${r.won}–${r.played-r.won}</span></td></tr>`);
 const page=paginate(ms);
 const scopes=['all','individual','team'].map(k=>`<button type="button" id="scope-${k}" class="seg-btn ${state.profileKind===k?'active':''}" aria-pressed="${state.profileKind===k}">${esc(t('scope_'+k))} · ${scopeCount(k)}</button>`).join('');
 return `<main class="container main">${crumb([['home',t('home')],['players',t('players')],['player/'+id,p.name]])}<div class="detailhead"><div class="detailhead-top"><div class="profile-head"><div class="avatar big">${esc(initials(p.name))}</div><div class="detail-title-area"><span class="kicker">${esc(regNo(id)||t('players'))}</span><h1 class="title-detail">${esc(p.name)}</h1><div class="detail-chips"><span>♧ ${esc(getClub(p.club_id).name)}${p.club_as_of?' · '+datefmt(p.club_as_of):''}</span>${latest?`<span>${esc(t('rank'))}: ${seniorFirst(ranks.filter(r=>r.date===latest.date)).map(r=>`#${esc(r.rank)} ${esc(r.category)}`).join(' · ')}${latest.points!=null?' · '+esc(fmtPoints(latest.points))+' '+esc(t('points')):''} · ${datefmt(latest.date)}</span>`:''}</div>${mergedNote(id)}</div></div><a class="ghost-btn small" href="${esc(h2hHref(id,''))}">${esc(t('compare'))} →</a></div></div>${rankingSection(ranks)}${statusBox(done.length?'statsNotComplete':'noPlayerMatches')}<div class="seg seg-wide" role="group" aria-label="${esc(t('type'))}">${scopes}</div><div class="results-grid"><div class="metric"><span>${esc(t('wins'))}</span><strong>${done.length?wins:'—'}</strong></div><div class="metric"><span>${esc(t('losses'))}</span><strong>${done.length?losses:'—'}</strong></div><div class="metric"><span>${esc(t('winRate'))}</span><strong>${rate===null?'—':rate+'%'}</strong></div></div>${done.length?playerInsights(done,id):''}${done.length?`<div class="profile-grid"><section><div class="section-header"><h3>${esc(t('bySeason'))}</h3></div>${dataTable(['season','events','played','wins','losses','winRate'],seasonRows)}</section><section><div class="section-header"><h3>${esc(t('eventsPlayed'))} · ${byEvent.size}</h3></div>${dataTable(['date','events','type','played','record'],eventRows)}</section></div>`:''}<div class="section-header"><h3>${esc(t('playerHistory'))}</h3></div>${dataTable(['date','opponent','score','events','source'],page.rows.map(m=>matchRow(m,id)),'noPlayerMatches')}${page.controls}<div class="section-header"><h3>${esc(t('doubles'))}</h3></div>${doublesTable((db.doubles||[]).filter(m=>[m.player1_id,m.partner1_id,m.player2_id,m.partner2_id].includes(id)))}<p class="source-note" style="margin-top:22px">${esc(t('statsNotComplete'))}</p></main>`;
}
// Club overview for one season (or all): the source's league positions, who played
// team matches for the club, and its fixtures seen from the club's side.
function clubPage(id){
 const c=clubById.get(id);if(!c)return notFound();
 const seasonOf=eventId=>getEvent(eventId).season||'';
 const allFixtures=db.fixtures.filter(f=>f.home_club_id===id||f.away_club_id===id);
 const byGroup=new Map();for(const r of db.standings){if(!byGroup.has(r.group_id))byGroup.set(r.group_id,[]);byGroup.get(r.group_id).push(r);}
 const tables=[...byGroup.values()].filter(g=>g.some(r=>r.club_id===id)),squad=db.clubPlayers[id]||[];
 const clubSeasons=[...new Set([...allFixtures.map(f=>seasonOf(f.event_id)),...tables.map(g=>seasonOf(g[0].event_id)),...squad.map(r=>seasonOf(r[0]))].filter(Boolean))].sort().reverse();
 const season=state.clubSeason==='all'||clubSeasons.includes(state.clubSeason)?state.clubSeason:(clubSeasons[0]||'all');
 const inSeason=eventId=>season==='all'||seasonOf(eventId)===season;
 const fs=allFixtures.filter(f=>inSeason(f.event_id)).sort((a,b)=>String(b.date).localeCompare(String(a.date)));
 const beat=f=>f.home_club_id===id?f.home_score>f.away_score:f.away_score>f.home_score;
 const done=fs.filter(f=>f.status==='completed'),wins=done.filter(beat).length,draws=done.filter(f=>f.home_score===f.away_score).length;
 const tally=list=>{const d=list.filter(f=>f.status==='completed');return d.length?`${d.filter(beat).length}–${d.length-d.filter(beat).length}`:'—';};
 const groupOf=f=>(String(f.source_url||'').match(/[?&]group=(\d+)/)||[])[1]||'';
 const entries=[],listed=new Set();
 for(const g of tables){if(!inSeason(g[0].event_id))continue;const places=standingPlaces(g);
  g.filter(r=>r.club_id===id).forEach((r,i)=>{listed.add(r.event_id);entries.push({event:getEvent(r.event_id),label:r.category,r,place:places.get(r.id),teams:g.length,archive:i?'':tally(fs.filter(f=>f.event_id===r.event_id&&groupOf(f)===r.group_id))});});}
 for(const eventId of new Set(fs.map(f=>f.event_id)))if(!listed.has(eventId))entries.push({event:getEvent(eventId),label:'',r:null,archive:tally(fs.filter(f=>f.event_id===eventId))});
 entries.sort((a,b)=>String(b.event.season||'').localeCompare(String(a.event.season||''))||String(b.event.start_date||'').localeCompare(String(a.event.start_date||''))||a.label.localeCompare(b.label,'el'));
 const clubTable=(columns,rows)=>`<div class="table-wrap club-table"><table><thead><tr>${columnHeads(columns)}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
 const competitionRows=entries.map(e=>{const under=[season==='all'?e.event.season:'',e.label].filter(Boolean).join(' · ');
  return `<tr><td>${link('#event/'+encodeURIComponent(e.event.id),e.event.name)}${under?`<div class="smalltext">${esc(under)}</div>`:''}</td><td>${e.r?`<strong>${esc(e.place)}</strong><span class="smallmuted"> / ${e.teams}</span>`:'—'}</td><td class="opt">${e.r?e.r.wins:'—'}</td><td class="opt">${e.r?e.r.losses:'—'}</td><td class="opt">${e.r?e.r.disqualified:'—'}</td><td>${e.r?`<strong>${e.r.points}</strong>`:'—'}</td><td>${esc(e.archive)}</td></tr>`;});
 const people=new Map();
 for(const [eventId,pid,played,won] of squad){if(!inSeason(eventId))continue;const o=people.get(pid)||{id:pid,events:new Set(),played:0,won:0};o.events.add(eventId);o.played+=played;o.won+=won;people.set(pid,o);}
 const playerRows=[...people.values()].sort((a,b)=>b.played-a.played||b.won-a.won||getPlayer(a.id).name.localeCompare(getPlayer(b.id).name,'el')).map(o=>`<tr><td>${link('#player/'+encodeURIComponent(o.id),getPlayer(o.id).name)}</td><td class="opt">${o.events.size}</td><td>${o.played}</td><td><span class="score">${o.won}–${o.played-o.won}</span></td><td class="opt">${Math.round(o.won/o.played*100)}%</td></tr>`);
 const page=paginate(fs);
 const fixtureRows=page.rows.map(f=>{const home=f.home_club_id===id,mine=home?f.home_score:f.away_score,theirs=home?f.away_score:f.home_score,other=home?f.away_club_id:f.home_club_id,played=f.status==='completed';
  return `<tr><td>${datefmt(f.date)}</td><td>${link('#club/'+encodeURIComponent(other),getClub(other).name)}</td><td><span class="score ${played&&mine!==theirs?(beat(f)?'win':'loss'):''}">${played?(beat(f)?'✓ ':mine===theirs?'':'✕ '):''}${mine??'—'}–${theirs??'—'}</span>${played?'':`<div class="smalltext">${esc(t(f.status))}</div>`}</td><td>${link('#event/'+encodeURIComponent(f.event_id),getEvent(f.event_id).name)}</td><td>${external(f.source_url,t('source'))}</td></tr>`;});
 // Roster: clubs as dated ranking observations, in the order of the latest official ranking.
 const index=rankingIndex(),latestRow=p=>(index.byPlayer.get(p.id)||[])[0];
 const roster=db.players.filter(p=>p.club_id===id).sort((a,b)=>{const x=latestRow(a),y=latestRow(b);return (x?0:1)-(y?0:1)||(x&&y?byCategory(x.category,y.category)||x.rank-y.rank:0)||a.name.localeCompare(b.name,'el');});
 const seasonFilter=clubSeasons.length?`<div class="filters"><label for="club-season">${esc(t('season'))}</label><select id="club-season" class="control"><option value="all" ${season==='all'?'selected':''}>${esc(t('allSeasons'))}</option>${clubSeasons.map(v=>`<option value="${esc(v)}" ${v===season?'selected':''}>${esc(v)}</option>`).join('')}</select></div>`:'';
 return `<main class="container main">${crumb([['home',t('home')],['clubs',t('clubs')],['club/'+id,c.name]])}<div class="detailhead"><span class="kicker">${esc(t('clubs'))}</span><h1 class="title-detail">${esc(c.name)}</h1><p>${esc(c.region||'')}</p>${c.aliases?`<div class="proof">${esc(t('alsoWritten'))}: ${esc(c.aliases.split('|').join(' · '))}</div>`:''}</div>${statusBox()}${seasonFilter}<h3>${esc(t('fixtureStats'))}</h3><div class="results-grid"><div class="metric"><span>${esc(t('wins'))}</span><strong>${wins}</strong></div><div class="metric"><span>${esc(t('losses'))}</span><strong>${done.length-wins-draws}</strong></div><div class="metric"><span>${esc(t('draws'))}</span><strong>${draws}</strong></div></div>${competitionRows.length?`<div class="section-header"><h3>${esc(t('scope_team'))} · ${competitionRows.length}</h3></div>${clubTable(['events','rank',['wins',1],['losses',1],['disq',1],'points','inArchive'],competitionRows)}<p class="source-note">${esc(t('clubNote'))}</p>`:''}${playerRows.length?`<div class="section-header"><h3>${esc(t('teamPlayers'))} · ${playerRows.length}</h3></div>${clubTable(['name',['events',1],'played','record',['winRate',1]],playerRows)}<p class="source-note">${esc(t('teamPlayersNote'))}</p>`:''}<div class="section-header"><h3>${esc(t('clubFixtures'))} · ${fs.length}</h3></div>${dataTable(['date','opponent','score','events','source'],fixtureRows,'noFixtures')}${page.controls}<div class="section-header"><h3>${esc(t('currentRoster'))} · ${roster.length}</h3></div>${roster.length?`<div class="white-panel">${roster.map(p=>{const r=latestRow(p);return `<div class="listrow"><div class="listmain"><div class="round-icon">${esc(p.name.charAt(0))}</div><div><div class="listname">${esc(p.name)}</div>${r?`<div class="listmeta">#${esc(r.rank)} ${esc(r.category)}${r.points!=null?' · '+esc(fmtPoints(r.points))+' '+esc(t('points')):''}</div>`:''}</div></div>${link('#player/'+encodeURIComponent(p.id),t('view')+' →')}</div>`;}).join('')}</div>`:empty('noPlayers')}</main>`;
}
// Movement since the category's previous list: places up or down, unchanged, or a new entry.
// Nothing is shown for a category's first list.
function rankMove(r){
 const prev=r.previous_rank;if(prev==null)return '';
 const el=state.lang==='el',d=prev?prev-r.rank:0,n=Math.abs(d);
 const [cls,mark,say]=!prev?['new',el?'ΝΕΟΣ':'NEW',el?'Νέα είσοδος στη λίστα':'New in this list']
  :!d?['same','=',el?'Ίδια θέση με την προηγούμενη λίστα':'Same place as in the previous list']
  :[d>0?'up':'down',(d>0?'▲':'▼')+n,el?`${n} ${n===1?'θέση':'θέσεις'} ${d>0?'πάνω':'κάτω'} από την προηγούμενη λίστα (#${prev})`:`${d>0?'Up':'Down'} ${n} ${n===1?'place':'places'} since the previous list (#${prev})`];
 return `<span class="move ${cls}" title="${esc(say)}"><span aria-hidden="true">${mark}</span><span class="sr-only">${esc(say)}</span></span>`;
}
function rankingsPage(){const hosted=db.meta.ranking_dates;const inCat=c=>state.rankCategory==='all'||c===state.rankCategory;const cats=sortCategories(hosted?Object.keys(hosted):new Set(db.rankings.map(r=>r.category)));const pool=state.rankDate!=='latest'&&db.rankingRows?db.rankingRows:db.rankings;const data=pool.filter(r=>inCat(r.category));const datesByCat=new Map();for(const r of data){const last=datesByCat.get(r.category);if(!last||last<r.date)datesByCat.set(r.category,r.date)}const dates=[...new Set(hosted?Object.entries(hosted).filter(([c])=>inCat(c)).flatMap(([,d])=>d):db.rankings.filter(r=>inCat(r.category)).map(r=>r.date))].sort().reverse();const rows=data.filter(r=>(state.rankDate==='latest'?datesByCat.get(r.category)===r.date:r.date===state.rankDate)&&rankingHit(r)).sort((a,b)=>byCategory(a.category,b.category)||a.rank-b.rank);const page=paginate(rows);const current=page.rows;return `<main class="container main">${crumb([['home',t('home')],['rankings',t('rankings')]])}<div class="paneltop"><div><span class="kicker">${esc(t('fromSource'))}</span><h2>${esc(t('rankings'))}</h2><p>${esc(t('statsNotComplete'))}</p></div></div>${statusBox()}${cats.length?`<div class="filters"><label class="sr-only" for="search-rankings">${esc(t('searchAthlete'))}</label><input class="control" type="search" id="search-rankings" placeholder="${esc(t('searchAthlete'))}" value="${esc(state.query)}"><label for="ranking-category">${esc(t('category'))}:</label><select id="ranking-category" class="control"><option value="all">${esc(t('allCategories'))}</option>${cats.map(c=>`<option value="${esc(c)}" ${c===state.rankCategory?'selected':''}>${esc(c)}</option>`).join('')}</select><label for="ranking-date">${esc(t('rankingDate'))}</label><select id="ranking-date" class="control"><option value="latest">${esc(t('latest'))}</option>${dates.map(d=>`<option value="${d}" ${d===state.rankDate?'selected':''}>${datefmt(d)}</option>`).join('')}</select></div>`:''}${state.query.trim()?`<p class="smallmuted" role="status">${rows.length} ${esc(t('rankingMatches'))}</p>`:''}${dataTable(['rank','move','name','category','points','date','source'],current.map(r=>`<tr><td><strong>#${r.rank}</strong></td><td>${rankMove(r)}</td><td>${link('#player/'+encodeURIComponent(r.player_id),getPlayer(r.player_id).name)}</td><td>${esc(r.category)}</td><td>${r.points==null?'—':esc(fmtPoints(r.points))}</td><td>${datefmt(r.date)}</td><td>${external(r.source_url,t('source'))}</td></tr>`),state.query.trim()?'tableEmpty':'noRankings')}${page.controls}</main>`;}
// Athlete search on the Rankings page: name/alias (Greek or Latin) or federation registration number.
function rankingHit(r){const q=state.query.trim();if(!q)return true;return searchHit(getPlayer(r.player_id),q)||(/^\d+$/.test(q)&&r.player_id==='httf-'+q);}
// One side of the comparison: the chosen athlete, or a search whose results are links.
function h2hSide(slot,id,other){
 const href=pick=>slot===1?h2hHref(pick,other):h2hHref(other,pick);
 if(id){const p=getPlayer(id);return `<div class="h2h-side"><div class="h2h-picked"><div class="avatar" aria-hidden="true">${esc(initials(p.name))}</div><div class="player-row-main">${link('#player/'+encodeURIComponent(id),p.name,'listname')}<div class="listmeta">${esc(clubLine(p.club_id,id))}</div></div><a class="ghost-btn small" href="${esc(href(''))}">${esc(t('change'))}</a></div></div>`;}
 const key='h2hQuery'+slot,q=state[key].trim(),label=t(slot===1?'playerOne':'playerTwo');
 // A number alone is also tried as a registration number. Athletes with more matches come first.
 const byReg=/^\d+$/.test(q)?playerById.get(keptId('players','httf-'+q)):null;
 const hits=q?[...(byReg?[byReg]:[]),...db.players.filter(p=>p!==byReg&&searchHit(p,q)).sort((a,b)=>playerTotals(b.id).played-playerTotals(a.id).played||a.name.localeCompare(b.name,'el'))].filter(p=>p.id!==other).slice(0,8):[];
 const results=q?`<div class="h2h-results" role="region" aria-label="${esc(t('results'))}">${hits.length?hits.map(p=>`<a class="search-hit" href="${esc(href(p.id))}"><span class="listname">${esc(p.name)}</span><span class="listmeta">${esc(clubLine(p.club_id,p.id))}</span></a>`).join(''):`<p class="search-none">${esc(t('tableEmpty'))}</p>`}</div>`:'';
 return `<div class="h2h-side"><label class="sr-only" for="h2h-search${slot}">${esc(label)}</label><input class="control" type="search" id="h2h-search${slot}" autocomplete="off" placeholder="${esc(label)}: ${esc(t('nameOrReg'))}" value="${esc(state[key])}">${results}</div>`;
}
// With one athlete chosen, their most-played opponents are one click away.
function h2hSuggestions(id,first){
 const counts=new Map();
 for(const m of completedForPlayer(id)){const o=m.player1_id===id?m.player2_id:m.player1_id;counts.set(o,(counts.get(o)||0)+1);}
 const top=[...counts.entries()].sort((a,b)=>b[1]-a[1]||getPlayer(a[0]).name.localeCompare(getPlayer(b[0]).name,'el')).slice(0,8);
 return top.length?`<div class="h2h-suggest"><span class="smallmuted">${esc(t('topOpponents'))}</span>${top.map(([o,n])=>`<a class="chip" href="${esc(first?h2hHref(id,o):h2hHref(o,id))}">${esc(getPlayer(o).name)} · ${n}</a>`).join('')}</div>`:'';
}
function h2hPage(){
 const [id1,id2]=h2hIds(),both=id1&&id2&&id1!==id2;
 const meetings=both?completedForPlayer(id1).filter(m=>[m.player1_id,m.player2_id].includes(id2)).sort((a,b)=>b.date.localeCompare(a.date)):[];
 const w1=meetings.filter(m=>m.winner_id===id1).length,w2=meetings.filter(m=>m.winner_id===id2).length;
 const body=both?`<div class="compareline"><span>${esc(getPlayer(id1).name)} · ${w1}</span><span>${w2} · ${esc(getPlayer(id2).name)}</span></div><div class="comparebar"><span style="width:${meetings.length?100*w1/meetings.length:50}%"></span><span style="width:${meetings.length?100*w2/meetings.length:50}%"></span></div>${dataTable(['date','opponent','score','events','source'],meetings.map(m=>matchRow(m,id1)),'noH2H')}`
  :id1&&id2?empty('selectTwo')
  :id1||id2?`${h2hSuggestions(id1||id2,!!id1)}<p class="source-note">${esc(t('h2hPickOther'))}</p>`
  :db.players.length<2?empty('missingPlayers'):`<p class="source-note">${esc(t('h2hHint'))}</p>`;
 return `<main class="container main">${crumb([['home',t('home')],['h2h',t('h2h')]])}<div class="paneltop"><div><span class="kicker">${esc(t('players'))}</span><h2>${esc(t('compare'))}</h2><p>${esc(t('statsNotComplete'))}</p></div></div><div class="white-panel"><div class="compare-selects">${h2hSide(1,id1,id2)}<div class="versus">VS</div>${h2hSide(2,id2,id1)}</div>${body}</div></main>`;
}
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
 ${batch?`<p>${batch.attempted}/${batch.eligible} ${batch.kind==='refresh'?esc(t('refreshChecked')):el?'πρόσθετες διοργανώσεις ελέγχθηκαν':'additional competitions checked'} · ${batch.pending} ${esc(t('pending'))} · ${batch.deferred.length} ${esc(t('deferred'))}. ${datefmt(batch.as_of)}</p>`:''}
 <p>${el?'Ο έλεγχος των δημόσιων σελίδων δεν αποδεικνύει πλήρες ιστορικό. Ορισμένες διοργανώσεις δεν έχουν αξιοποιήσιμα αποτελέσματα.':'Checking public pages does not establish complete history. Some competitions have no usable results.'}</p>
 <div class="link-row"><a class="text-link" href="coverage.json" download>${esc(t('coverageReport'))} (JSON)</a><a class="text-link" href="provenance.json" download>${esc(t('provenanceReport'))} (JSON)</a>${db.meta.ranking_history&&db.meta.partitions?`<a class="text-link" href="ranking-history-provenance.json" download>${esc(t('rankingHistoryReport'))} (JSON)</a>`:''}${db.meta.league_standings&&db.meta.partitions?`<a class="text-link" href="standings-provenance.json" download>${esc(t('standingsReport'))} (JSON)</a>`:''}</div>
 ${dataTable(['season','checked','deferred','withResults','results','doubles'],summary)}
 <p>${el?'Στιγμιότυπα κατάταξης':'Ranking snapshots'}: ${Object.entries((coverage.rankings||[]).reduce((m,r)=>{(m[r.category]=m[r.category]||[]).push(r);return m},{})).map(([c,rs])=>{const ds=rs.map(r=>r.date).sort();return `${esc(c)} · ${datefmt(ds[0])} – ${datefmt(ds[ds.length-1])} (${rs.length})`}).join('; ')}</p>
 <div class="filters"><label for="season-filter">${esc(t('season'))}</label><select id="season-filter" class="control"><option value="all">${esc(t('allSeasons'))}</option>${seasons.map(v=>`<option value="${esc(v)}" ${v===state.season?'selected':''}>${esc(v)}</option>`).join('')}</select><label class="sr-only" for="search-events">${esc(t('search'))}</label><input id="search-events" type="search" class="control" value="${esc(state.query)}" placeholder="${esc(t('search'))}"></div>
 ${dataTable(['events','results','doubles','fixtures','status'],rows)}${page.controls}</div>`;
}
// How to report a mistake or ask for removal, and the reviewed identity corrections in this build.
function correctionsPanel(){
 const n=Object.keys(corrected.players||{}).length+Object.keys(corrected.clubs||{}).length;
 return `<div class="white-panel" style="margin-top:24px"><h3>${esc(t('corrections'))}</h3><p>${esc(t('correctionsText'))}</p><p class="source-note">${esc(t('correctionsPublic'))}</p>${n?`<p>${n} ${esc(t('identityFixes'))}.</p>`:''}<div class="link-row">${external(REPORT_URL,t('reportIssue'))}${n&&db.meta.partitions?`<a class="text-link" href="identity-corrections.json" download>${esc(t('identityReport'))} (JSON)</a>`:''}</div></div>`;
}
// Feedback form (#feedback). The site has no server, so the browser posts the message to
// Web3Forms, which forwards it by email. FEEDBACK_KEY is that service's access key; it is
// public by design (all it can do is send mail to its owner). While it is empty the form,
// the links to it and its route are absent.
const FEEDBACK_URL='https://api.web3forms.com/submit';
const FEEDBACK_KEY='e4632a59-f88d-4593-a338-f8254e0a719f';
const FEEDBACK_TOPICS=['idea','broken','unclear','other'];
const feedbackOn=()=>!!FEEDBACK_KEY;
// What the visitor has typed lives here, so a re-render (a language switch, a failed send) keeps it.
// `from` is the page they were on before opening the form; `trap` is a field people never see.
const fb={topic:'idea',message:'',email:'',trap:'',status:'idle',error:'',from:''};
function feedbackPage(){
 const el=state.lang==='el';
 const head=`<main class="container main">${crumb([['home',t('home')],['feedback',t('feedback')]])}<div class="paneltop"><div><span class="kicker">${esc(t('feedback'))}</span><h2>${esc(t('fbTitle'))}</h2><p>${esc(t('fbIntro'))}</p></div></div>`;
 if(fb.status==='sent')return head+`<div class="white-panel feedback-panel" role="status"><h3>${esc(t('fbThanks'))}</h3><p>${esc(t('fbThanksText'))}</p><div class="link-row"><button class="ghost-btn" id="fb-again" type="button">${esc(t('fbAgain'))}</button><a class="ghost-btn" href="${esc(fb.from||'#home')}">${esc(t('goBack'))}</a></div></div></main>`;
 const busy=fb.status==='sending';
 const page=fb.from?(el?`η σελίδα από την οποία ήρθατε (${fb.from}), `:`the page you came from (${fb.from}), `):'';
 const sentWith=el?`Μαζί με το μήνυμα στέλνονται ${page}η έκδοση του ιστότοπου και η γλώσσα. Το μήνυμα παραδίδεται με email μέσω της υπηρεσίας Web3Forms.`:`Sent with your message: ${page}the site version and the language. The message is delivered by email through the Web3Forms service.`;
 return head+`<form class="white-panel feedback-panel" id="feedback-form">`
  +`<div class="field"><label for="fb-topic">${esc(t('fbTopic'))}</label><select class="control" id="fb-topic">${FEEDBACK_TOPICS.map(k=>`<option value="${k}"${fb.topic===k?' selected':''}>${esc(t('fbTopic_'+k))}</option>`).join('')}</select></div>`
  +`<div class="field"><label for="fb-message">${esc(t('fbMessage'))}</label><textarea class="control" id="fb-message" rows="7" maxlength="4000" required>${esc(fb.message)}</textarea></div>`
  +`<div class="field"><label for="fb-email">${esc(t('fbEmail'))} <em>(${esc(t('fbOptional'))})</em></label><input class="control" type="email" id="fb-email" autocomplete="email" maxlength="200" value="${esc(fb.email)}" aria-describedby="fb-email-note"><small id="fb-email-note">${esc(t('fbEmailNote'))}</small></div>`
  +`<div hidden><label for="fb-website">Website</label><input id="fb-website" tabindex="-1" autocomplete="off" value="${esc(fb.trap)}"></div>`
  +(fb.error?`<p class="form-error" role="alert">${esc(t(fb.error))}</p>`:'')
  +`<button class="primary-btn" type="submit"${busy?' disabled':''}>${esc(t(busy?'fbSending':'fbSend'))}</button>`
  +`<p class="source-note">${esc(sentWith)}</p><p class="source-note">${esc(t('fbCorrections'))} ${external(REPORT_URL,t('reportIssue'))}</p></form></main>`;
}
function sendFeedback(){
 if(fb.status==='sending')return;
 const message=fb.message.trim(),email=fb.email.trim();
 fb.error=!message?'fbEmpty':email&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)?'fbBadEmail':'';
 if(fb.error){render();return;}
 // Only a script fills the hidden field: it gets the thanks and nothing is sent.
 if(fb.trap){fb.status='sent';fb.message='';render();return;}
 const body={access_key:FEEDBACK_KEY,subject:`${SITE_TITLE} feedback: ${dictionary.en['fbTopic_'+fb.topic]}`,from_name:SITE_TITLE,topic:dictionary.en['fbTopic_'+fb.topic],message,page:fb.from||'(opened directly)',version:db.meta.version||'',language:state.lang};
 if(email)body.email=email;
 fb.status='sending';render();
 Promise.resolve().then(()=>fetch(FEEDBACK_URL,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(body)}))
  .then(response=>response.json().then(reply=>{if(!response.ok||!reply||reply.success!==true)throw new Error('Feedback was not accepted');}))
  .then(()=>{fb.status='sent';fb.message='';},()=>{fb.status='idle';fb.error='fbFailed';})
  .then(()=>{if(hashRoute().view==='feedback')render();});
}
// Where the form is offered from the About page.
function feedbackPanel(){return feedbackOn()?`<div class="white-panel" style="margin-top:24px"><h3>${esc(t('feedback'))}</h3><p>${esc(t('fbAbout'))}</p><div class="link-row">${link('#feedback',t('fbOpen')+' →')}</div></div>`:'';}
function aboutPage(){return `<main class="container main">${crumb([['home',t('home')],['about',t('about')]])}<div class="paneltop"><div><span class="kicker">${esc(t('openData'))}</span><h2>${esc(t('dataTransparency'))}</h2></div></div><div class="info-grid" style="margin-top:0"><div class="white-panel"><h3>${esc(t('dataTransparency'))}</h3><p>${esc(t('dataTransparencyText'))}</p><p>${esc(t('statsNotComplete'))}</p><div class="link-row">${external('https://app.ttscore.io/customer/24',t('viewSource'))}</div></div><div class="white-panel"><h3>${esc(t('importStatus'))}</h3><div class="progress"><span>${db.events.length} ${esc(t('events'))}</span><span>${db.players.length} ${esc(t('players'))}</span><span>${totalSingles()} ${esc(t('results'))}</span><span>${totalDoubles()} ${esc(t('doubles'))}</span><span>${db.meta.table_counts?.rankings??db.rankings.length} ${esc(t('rankings'))}</span></div><p style="margin-top:20px">${esc(t('coverage'))} · ${esc((db.meta.dataset_sha256||'').slice(0,16))}</p>${freshness()}</div><div class="white-panel"><h3>${esc(t('architecture'))}</h3><p>${esc(t('architectureText'))}</p><p>${esc(t('openData'))}</p></div><div class="white-panel"><h3>${esc(t('importPlan'))}</h3><p>${esc(t('importPlanText'))}</p><p class="source-note">CSV → Python validation → static HTML → GitHub Pages.</p></div></div>${correctionsPanel()}${feedbackPanel()}${privacyPanel()}${coverageDetails()}${db.meta.partitions?`<p class="source-note"><a class="text-link" href="offline.html" download>${state.lang==='el'?'Λήψη πλήρους αρχείου για χρήση χωρίς σύνδεση':'Download complete archive for offline use'} (HTML)</a></p>`:''}</main>`;}
// Privacy notice for the people named in the archive (GDPR Article 14) and for visitors.
// PRIVACY_CONTACT is the published controller identity: fill in `operator` (who runs the site)
// and `email` (a private route for requests). While `email` is empty, requests go to the
// public issue form, and the notice says that they are public.
const PRIVACY_CONTACT={operator:'',email:'',requestUrl:REPORT_URL};
const FEEDBACK_PRIVACY_URL='https://web3forms.com/privacy';
function privacyPanel(){
 const el=state.lang==='el',{operator,email,requestUrl}=PRIVACY_CONTACT;
 const mail=/^[^\s@<>"]+@[^\s@<>"]+\.[^\s@<>"]+$/.test(email)?`<a class="text-link" href="mailto:${esc(email)}">${esc(email)}</a>`:'';
 const item=(title,text)=>`<p><strong>${esc(title)}</strong> ${text}</p>`;
 const who=el
  ?`Το Greek TT Archive είναι ανεξάρτητο έργο ανοιχτού κώδικα, χωρίς διαφημίσεις ή συνδρομές. Δεν το διαχειρίζεται η ΕΦΟΕπΑ ούτε το TTScore.${operator?` Υπεύθυνος επεξεργασίας: ${esc(operator)}.`:''}`
  :`Greek TT Archive is an independent open-source project with no advertising or subscriptions. It is not run by the Hellenic Table Tennis Federation (HTTF) or by TTScore.${operator?` Data controller: ${esc(operator)}.`:''}`;
 const contact=mail
  ?(el?`Γράψτε στο ${mail} με το ονοματεπώνυμο ή τον αριθμό μητρώου (ΑΜ) του προφίλ.`:`Write to ${mail} with the name or registration number (Reg.) shown on the profile.`)
  :(el?'Στείλτε αίτημα από τον παρακάτω σύνδεσμο, με το ονοματεπώνυμο ή τον αριθμό μητρώου (ΑΜ) του προφίλ. Τα αιτήματα στο GitHub είναι δημόσια: μη γράφετε περισσότερα προσωπικά στοιχεία από όσα χρειάζονται.':'Send a request from the link below, with the name or registration number (Reg.) shown on the profile. Requests on GitHub are public: include no more personal detail than needed.');
 const hosting=db.meta.partitions?(el?' Φιλοξενείται στο GitHub Pages, που καταγράφει τεχνικά στοιχεία σύνδεσης όπως τη διεύθυνση IP.':' It is hosted on GitHub Pages, which logs technical connection details such as your IP address.'):'';
 // What the feedback form sends and where it goes; shown only while the form is switched on.
 // Retention, transfers and spam filtering are as Web3Forms' privacy policy states them (13 Jul 2026).
 const feedback=!feedbackOn()?'':el
  ?item('Φόρμα σχολίων.','Η χρήση της φόρμας είναι προαιρετική. Στέλνει το θέμα και το μήνυμά σας, το email σας αν το δώσετε, τη σελίδα από την οποία ήρθατε, την έκδοση του ιστότοπου και τη γλώσσα. Ο browser σας τα στέλνει στην υπηρεσία Web3Forms, που τα προωθεί με email στα εισερχόμενα του διαχειριστή του ιστότοπου. Η Web3Forms λαμβάνει επίσης τη διεύθυνση IP σας. Σύμφωνα με την πολιτική απορρήτου της, μπορεί να διαβιβάσει την IP και το email σε φίλτρα ανεπιθύμητων μηνυμάτων, λειτουργεί από την Ινδία (οι διαβιβάσεις από την ΕΕ βασίζονται σε τυποποιημένες συμβατικές ρήτρες) και διατηρεί τις υποβολές έως τρία χρόνια.')
  :item('Feedback form.','Using the form is optional. It sends your topic and message, your email address if you give one, the page you came from, the site version and the language. Your browser sends these to Web3Forms, a form-to-email service, which forwards them by email to the site owner\'s inbox. Web3Forms also receives your IP address. Its privacy policy says that it may pass the IP and email address to spam filters, that it operates from India (transfers from the EU rely on Standard Contractual Clauses) and that it keeps submissions for up to three years.');
 return `<div class="white-panel" style="margin-top:24px"><h3>${el?'Προσωπικά δεδομένα':'Privacy and personal data'}</h3><p>${who}</p>${el
  ?item('Τι δημοσιεύεται.','Ονοματεπώνυμο, αριθμός μητρώου ομοσπονδίας, σωματείο, αγωνιστική και ηλικιακή κατηγορία, αποτελέσματα αγώνων και θέσεις στην επίσημη κατάταξη. Τα στοιχεία προέρχονται από τις δημόσιες σελίδες της ΕΦΟΕπΑ στο TTScore· δεν συλλέγονται από τους ίδιους τους αθλητές.')
   +item('Τι δεν δημοσιεύεται.','Ημερομηνία ή έτος γέννησης, εθνικότητα, στοιχεία επικοινωνίας και σημειώσεις μητρώου.')
   +item('Σκοπός και νομική βάση.','Η τήρηση ενός αναζητήσιμου αρχείου της ελληνικής αγωνιστικής επιτραπέζιας αντισφαίρισης: αποτελέσματα, στατιστικά και ιστορικό κατάταξης. Νομική βάση είναι το έννομο συμφέρον για την τεκμηρίωση δημόσιων αγωνιστικών αποτελεσμάτων (άρθρο 6 παρ. 1 στοιχ. στ΄ ΓΚΠΔ). Τα στοιχεία παραμένουν όσο δημοσιεύεται το αρχείο ή μέχρι να ζητηθεί η αφαίρεσή τους.')
   +item('Τα δικαιώματά σας.','Μπορείτε να ζητήσετε αντίγραφο, διόρθωση ή αφαίρεση των στοιχείων που σας αφορούν, ή να αντιταχθείτε στη δημοσίευσή τους. Για ανήλικους αθλητές το αίτημα μπορεί να το υποβάλει γονέας ή κηδεμόνας. Τα αιτήματα αφαίρεσης γίνονται σεβαστά και απαντώνται εντός ενός μηνός. Έχετε επίσης δικαίωμα καταγγελίας στην Αρχή Προστασίας Δεδομένων Προσωπικού Χαρακτήρα.')
   +item('Επικοινωνία.',contact)
   +item('Επισκέπτες.',`Ο ιστότοπος δεν χρησιμοποιεί cookies, στατιστικά επισκεψιμότητας ή διαφημίσεις· αποθηκεύει μόνο την επιλογή γλώσσας στον browser σας.${hosting}`)
  :item('What is published.','Name, federation registration number, club, competition and age category, match results and official ranking positions. The records come from the HTTF public pages on TTScore; they are not collected from the athletes themselves.')
   +item('What is not published.','Date or year of birth, nationality, contact details and registration notes.')
   +item('Purpose and legal basis.','To keep a searchable record of competitive table tennis in Greece: results, statistics and ranking history. The legal basis is the legitimate interest in documenting public sporting results (GDPR Article 6(1)(f)). Records stay for as long as the archive is published, or until their removal is requested.')
   +item('Your rights.','You can ask for a copy, a correction or the removal of records about you, or object to their publication. For an athlete who is a minor, a parent or guardian can make the request. Removal requests are honoured and answered within one month. You also have the right to complain to the Hellenic Data Protection Authority.')
   +item('Contact.',contact)
   +item('Visitors.',`The site uses no cookies, analytics or advertising; it stores only your language choice in your browser.${hosting}`)
  }${feedback}<div class="link-row">${mail?'':external(requestUrl,el?'Αίτημα διόρθωσης ή αφαίρεσης':'Request a correction or removal')}${external('https://www.dpa.gr/',el?'Αρχή Προστασίας Δεδομένων':'Hellenic Data Protection Authority')}${feedback?external(FEEDBACK_PRIVACY_URL,el?'Πολιτική απορρήτου Web3Forms':'Web3Forms privacy policy'):''}</div></div>`;
}
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
 for(const [id,list] of byPlayer)byPlayer.set(id,seniorFirst(list));
 return rankIndexCache={latestDate,byPlayer,cats:sortCategories(latestDate.keys())};
}
function sectionSwitch(active){return `<div class="seg" role="navigation">${['events','players'].map(k=>`<a class="seg-btn ${active===k?'active':''}" href="#${k}" ${active===k?'aria-current="page"':''}>${esc(t(k))}</a>`).join('')}</div>`;}
function eventRow(e){
 const n=completedByEvent.get(e.id)||0,k=eventKind(e);
 // The dates place a competition in its season; the season is shown only when no date is known.
 const dates=e.start_date&&e.end_date&&e.start_date!==e.end_date?`${datefmt(e.start_date)} – ${datefmt(e.end_date)}`:e.start_date||e.end_date?datefmt(e.start_date||e.end_date):esc(e.season||'—');
 return `<a class="event-row" href="#event/${encodeURIComponent(e.id)}"><div class="event-badge kind-${k}" aria-hidden="true">${kindIcon[k]}</div><div class="event-row-main"><h3>${eventName(e)}</h3><div class="event-row-meta">${kindTag(e)}<span>${dates}</span>${e.region?`<span class="ellipsis">${esc(e.region)}</span>`:''}</div></div><div class="event-row-stats">${n?`<span><b>${n}</b> ${esc(t('matchesShort'))}</span><span><b>${eventPlayers(e.id)}</b> ${esc(t('playersShort'))}</span>`:`<span class="smallmuted">${esc(t(k==='unchecked'?'pending':'noResultsYet'))}</span>`}</div><span class="event-row-go" aria-hidden="true">›</span></a>`;
}
// Won–lost with a proportion bar. The label says the same in words for screen readers.
function winLoss(played,won){
 if(!played)return `<div class="wl"><span class="smalltext">${esc(t('noMatchesImported'))}</span></div>`;
 const lost=played-won;
 return `<div class="wl" role="img" aria-label="${played} ${esc(t('matchesShort'))}: ${won} ${esc(lower(t('wins')))}, ${lost} ${esc(lower(t('losses')))}"><span class="wl-rec"><b class="won">${won}</b><i>–</i><b class="lost">${lost}</b></span><span class="wl-bar"><i style="width:${Math.round(100*won/played)}%"></i></span></div>`;
}
const clubLine=(club,id)=>[club?getClub(club).name:'',regNo(id)].filter(Boolean).join(' · ');
function eventSummary(ms){
 const rows=new Map();
 for(const m of ms){if(m.status!=='completed')continue;
  // Club comes from the match sheet: profile clubs are dated ranking observations.
  for(const [pid,club] of [[m.player1_id,m.club1_id],[m.player2_id,m.club2_id]]){const r=rows.get(pid)||{id:pid,club:'',played:0,won:0};r.played++;if(m.winner_id===pid)r.won++;if(club)r.club=club;rows.set(pid,r);}}
 return [...rows.values()].sort((a,b)=>b.won-a.won||(a.played-a.won)-(b.played-b.won)||getPlayer(a.id).name.localeCompare(getPlayer(b.id).name,'el'));
}
function eventPlayerRow(r){const p=getPlayer(r.id);return `<div class="player-row"><div class="avatar" aria-hidden="true">${esc(initials(p.name))}</div><div class="player-row-main">${link('#player/'+encodeURIComponent(r.id),p.name,'listname')}<div class="listmeta">${esc(clubLine(r.club,r.id))}</div></div>${winLoss(r.played,r.won)}<button type="button" class="text-link" data-event-player="${esc(r.id)}">${esc(t('showMatches'))} →</button></div>`;}
// A two-line scoreboard: one line per player, the winner first, each game in its own column.
function matchEntry(m){
 const done=m.status==='completed',flip=done&&m.winner_id===m.player2_id;
 const [a,b]=flip?[m.player2_id,m.player1_id]:[m.player1_id,m.player2_id],[ca,cb]=flip?[m.club2_id,m.club1_id]:[m.club1_id,m.club2_id];
 const sa=flip?m.score2:m.score1,sb=flip?m.score1:m.score2;
 const has=v=>v!==null&&v!==undefined&&v!=='';
 const games=(m.games||[]).map(g=>flip?[g[1],g[0]]:g);
 const line=(pid,club,sets,i,win)=>`<div class="mr-line ${win?'win':''}"><span class="mr-mark">${win?`<span aria-hidden="true">✓</span><span class="sr-only">${esc(t('winner'))}</span>`:''}</span><span class="mr-player">${link('#player/'+encodeURIComponent(pid),getPlayer(pid).name,'listname')}${club?`<span class="listmeta">${esc(getClub(club).name)}</span>`:''}</span><span class="mr-sets">${has(sets)?esc(sets):'—'}</span><span class="mr-games">${games.map(g=>Number(g[i])>Number(g[1-i])?`<b>${esc(g[i])}</b>`:`<span>${esc(g[i])}</span>`).join('')}</span></div>`;
 return `<article class="match-row" aria-label="${esc(getPlayer(a).name)} – ${esc(getPlayer(b).name)}${has(sa)&&has(sb)?` ${esc(sa)}–${esc(sb)}`:''}"><div class="mr-meta"><span class="mr-date">${datefmt(m.date)}</span><span>${esc(t(m.phase||'league'))}${m.category?' · '+esc(m.category):''}</span>${done?'':`<span class="mr-status">${esc(t(m.status))}</span>`}</div><div class="mr-board">${line(a,ca,sa,0,done&&m.winner_id===a)}${line(b,cb,sb,1,false)}</div><div class="mr-src">${external(m.source_url,t('source'))}</div></article>`;
}
// The list the Athletes page shows: a chosen tab, else the first senior list (men); a
// search before any tab is chosen covers every athlete.
function rosterCategory(){return state.rosterCat||(state.query.trim()?'all':rankingIndex().cats[0]||'all');}
// Every published snapshot date of a category, newest first.
function snapshotDates(cat){
 const hosted=db.meta.ranking_dates;
 return hosted?[...(hosted[cat]||[])].sort().reverse():[...new Set(db.rankings.filter(r=>r.category===cat).map(r=>r.date))].sort().reverse();
}
// A month as it stands alone ("Οκτώβριος", "October"): the form a month takes next to a year.
function monthName(date){
 const part=new Intl.DateTimeFormat(state.lang==='el'?'el-GR':'en-GB',{month:'long',year:'numeric',timeZone:'UTC'}).formatToParts(new Date(date+'T12:00:00Z')).find(x=>x.type==='month');
 return part?part.value:date.slice(5,7);
}
// Year and month of the snapshot to list. Two snapshots in one month also show their day.
function snapshotPicker(dates,shown,latest){
 const year=shown.slice(0,4),years=[...new Set(dates.map(d=>d.slice(0,4)))];
 const perMonth=new Map();for(const d of dates)perMonth.set(d.slice(0,7),(perMonth.get(d.slice(0,7))||0)+1);
 const months=dates.filter(d=>d.startsWith(year)).map(d=>`<option value="${d}" ${d===shown?'selected':''}>${esc(monthName(d))}${perMonth.get(d.slice(0,7))>1?' · '+Number(d.slice(8)):''}</option>`).join('');
 return `<span class="snap-pick"><label class="sr-only" for="roster-year">${esc(t('snapYear'))}</label><select id="roster-year" class="control">${years.map(y=>`<option value="${y}" ${y===year?'selected':''}>${y}</option>`).join('')}</select><label class="sr-only" for="roster-month">${esc(t('snapMonth'))}</label><select id="roster-month" class="control">${months}</select>${shown!==latest?`<button type="button" id="roster-latest" class="ghost-btn small">${esc(t('snapLatest'))}</button>`:''}</span>`;
}
function playersPage(){
 const idx=rankingIndex(),cat=rosterCategory();
 const sort=['rank','played','name'].includes(state.rosterSort)?state.rosterSort:'rank';
 // A chosen list holds one snapshot: the latest, or a past one from its own file.
 const latest=cat==='all'?'':idx.latestDate.get(cat)||'',dates=cat==='all'?[]:snapshotDates(cat);
 const shown=state.rosterDate&&dates.includes(state.rosterDate)?state.rosterDate:latest,past=shown!==latest;
 const snapshot=new Map();
 if(cat!=='all'){const pool=past&&db.meta.partitions?db.rankingRows||[]:db.rankings;for(const r of pool)if(r.category===cat&&r.date===shown)snapshot.set(r.player_id,r);}
 // The position a row shows: in the chosen list, or for all athletes in the most senior list they hold.
 const rankIn=p=>cat==='all'?(idx.byPlayer.get(p.id)||[])[0]:snapshot.get(p.id);
 // A chosen list is read from its own rows, so an athlete listed then is never missed.
 let rows=(cat==='all'?db.players:[...snapshot.keys()].map(getPlayer)).filter(p=>searchHit(p,state.query));
 const totals=new Map(rows.map(p=>[p.id,playerTotals(p.id)]));
 const byName=(a,b)=>a.name.localeCompare(b.name,'el');
 const byPlayed=(a,b)=>totals.get(b.id).played-totals.get(a.id).played||byName(a,b);
 // By official position; at the same position the senior lists go in their usual order (men, women).
 // Athletes with no official ranking follow, the ones with more imported matches first.
 const byRank=(a,b)=>{const x=rankIn(a),y=rankIn(b);return (x?0:1)-(y?0:1)||(x&&y?x.rank-y.rank||byCategory(x.category,y.category)||byName(a,b):byPlayed(a,b));};
 rows.sort(sort==='rank'?byRank:sort==='played'?byPlayed:byName);
 const page=paginate(rows),from=state.page*50;
 const sorts=['rank','played','name'].map(s=>`<option value="${s}" ${s===sort?'selected':''}>${esc(t('sort_'+s))}</option>`).join('');
 // A past list shows each athlete's club as that list gave it.
 const list=page.rows.map(p=>{const tot=totals.get(p.id),held=idx.byPlayer.get(p.id)||[],r=rankIn(p),club=past&&r&&r.club_id?r.club_id:p.club_id;
  return `<a class="player-row" href="#player/${encodeURIComponent(p.id)}"><div class="rank-num">${r?r.rank+rankMove(r):'<span class="smalltext">—</span>'}</div><div class="avatar" aria-hidden="true">${esc(initials(p.name))}</div><div class="player-row-main"><div class="listname">${esc(p.name)}</div><div class="listmeta">${esc(clubLine(club,p.id))}</div></div><div class="points">${r?`<b>${r.points==null?'—':esc(fmtPoints(r.points))}</b><span class="smalltext">${esc(r.category)}${cat==='all'&&held.length>1?` +${held.length-1}`:''} · ${datefmt(r.date)}</span>`:`<span class="smalltext">${esc(t('unranked'))}</span>`}</div>${winLoss(tot.played,tot.won)}</a>`;}).join('');
 const cols=`<div class="list-cols" aria-hidden="true"><span class="num">${esc(t('rankShort'))}</span><span></span><span>${esc(t('name'))}</span><span class="num">${esc(t('points'))}</span><span class="num">${esc(t('record'))}</span></div>`;
 const tabs=idx.cats.length?`<div class="subtabs roster-tabs" role="tablist" aria-label="${esc(t('category'))}">${['all',...idx.cats].map((c,i)=>`<button type="button" role="tab" id="roster-tab-${i}" class="subtab ${c===cat?'active':''}" aria-selected="${c===cat}">${esc(c==='all'?t('anyRanking'):c)}</button>`).join('')}</div>`:'';
 const title=cat==='all'?t('playerList'):`${cat} · ${datefmt(shown)}`;
 return `<main class="container main">${crumb([['home',t('home')],['players',t('players')]])}${sectionSwitch('players')}<div class="searchpanel">${tabs}<div class="filters" style="margin:0"><label class="sr-only" for="search-roster">${esc(t('search'))}</label><input class="control" type="search" id="search-roster" placeholder="${esc(t('search'))}" value="${esc(state.query)}">${dates.length?snapshotPicker(dates,shown,latest):''}<label class="sr-only" for="roster-sort">${esc(t('sortBy'))}</label><select id="roster-sort" class="control">${sorts}</select></div></div>${statusBox()}<div class="list-head"><span class="list-title">${esc(title)}</span><span class="smallmuted">${rows.length?`${from+1}–${from+page.rows.length} / ${rows.length}`:''}</span></div>${list?`<div class="player-list is-roster">${cols}${list}</div>`:empty('noPlayers')}${page.controls}</main>`;
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
// Age categories are filtered views of one federation ranking: a player has one points
// value per date and a separate position in each category. Order categories senior first.
const CATEGORY_ORDER=['Άνδρες','Γυναίκες','Νέοι Άνδρες','Νέες Γυναίκες','Έφηβοι','Νεανίδες','Παίδες','Κορασίδες','Παμπαίδες','Παγκορασίδες','Μίνι Παμπαίδων','Μίνι Παγκορασίδων'];
const categoryRank=c=>{const i=CATEGORY_ORDER.indexOf(c);return i<0?CATEGORY_ORDER.length:i;};
const byCategory=(a,b)=>categoryRank(a)-categoryRank(b)||a.localeCompare(b,'el');
const sortCategories=cats=>[...cats].sort(byCategory);
const seniorFirst=rows=>[...rows].sort((a,b)=>byCategory(a.category,b.category));
function rankingChart(ranks){
 const byDate=new Map();for(const r of ranks){if(!byDate.has(r.date))byDate.set(r.date,[]);byDate.get(r.date).push(r);}
 const scored=r=>r.points!==null&&r.points!==undefined&&r.points!=='';
 // One line across all categories when every date carries a single points value
 // (as TTScore publishes it); otherwise fall back to one category at a time.
 const shared=ranks.every(scored)&&[...byDate.values()].every(rs=>new Set(rs.map(r=>Number(r.points))).size===1);
 const cats=sortCategories(new Set(ranks.map(r=>r.category)));
 const newest=[...byDate.keys()].sort().pop();
 const cat=shared?null:cats.includes(state.chartCat)?state.chartCat:seniorFirst(byDate.get(newest))[0].category;
 const own=shared?[]:ranks.filter(r=>r.category===cat);
 const byPoints=shared||own.every(scored);
 const series=shared?[...byDate.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([date,rs])=>({date,value:Number(rs[0].points),rows:seniorFirst(rs)}))
  :own.sort((a,b)=>a.date.localeCompare(b.date)).map(r=>({date:r.date,value:Number(byPoints?r.points:r.rank),rows:[r]}));
 const range=state.chartRange in CHART_RANGES?state.chartRange:'all';
 const day=86400000,toMs=d=>Date.parse(d+'T00:00:00Z'),lastMs=toMs(series[series.length-1].date);
 let start=null;if(CHART_RANGES[range]){const d=new Date(lastMs);d.setUTCMonth(d.getUTCMonth()-CHART_RANGES[range]);start=d.getTime();}
 const shown=series.filter(s=>start===null||toMs(s.date)>=start);
 let t0=start??toMs(shown[0].date),t1=lastMs;if(t0===t1){t0-=15*day;t1+=15*day;}
 const y=niceTicks(Math.min(...shown.map(s=>s.value)),Math.max(...shown.map(s=>s.value)));
 const xPct=ms=>3+94*(ms-t0)/(t1-t0);
 // Points: higher is better. Rank fallback: position 1 sits at the top.
 const yPct=v=>6+88*(byPoints?(y.hi-v):(v-y.lo))/(y.hi-y.lo);
 const num=new Intl.NumberFormat(state.lang==='el'?'el-GR':'en-US',{maximumFractionDigits:1});
 const xt=monthTicks(t0,t1);
 const pts=shown.map(s=>{const i=series.indexOf(s),prev=series[i-1],delta=prev?s.value-prev.value:null,x=xPct(toMs(s.date)),yy=yPct(s.value);
  const change=delta===null||delta===0?'':` (${delta>0?'+':'−'}${num.format(Math.abs(delta))})`;
  const places=s.rows.map(r=>`#${r.rank} · ${r.category}`);
  const label=`${datefmt(s.date)}: ${byPoints?num.format(s.value)+' '+t('points').toLowerCase()+' · ':''}${places.join(', ')}${change}`;
  return {x,yy,html:`<span class="pt" tabindex="0" role="img" aria-label="${esc(label)}" style="left:${x.toFixed(2)}%;top:${yy.toFixed(2)}%"><span class="tip ${x>70?'tip-left':''} ${yy<28?'tip-below':''}">${datefmt(s.date)} : <b>${esc(byPoints?num.format(s.value):'#'+s.value)}</b>${esc(change)}${places.map(p=>`<br>${esc(p)}`).join('')}</span></span><i class="guide" style="top:${yy.toFixed(2)}%"></i>`};});
 const ranges=Object.keys(CHART_RANGES).map(k=>`<button type="button" id="range-${k}" class="${k===range?'active':''}" aria-pressed="${k===range}">${esc(t('range_'+k))}</button>`).join('');
 return `<div class="rchart ${shown.length>36?'dense':''}"><div class="rchart-head"><h3>${esc(t(byPoints?'chartTitle':'chartTitleRank'))}</h3><div class="rchart-ranges" role="group">${ranges}</div></div>${shared?(cats.length>1?`<p class="source-note">${esc(t('sharedPoints'))}: ${esc(cats.join(', '))}</p>`:''):cats.length>1?`<div class="filters"><label for="chart-category">${esc(t('category'))}</label><select id="chart-category" class="control">${cats.map(c=>`<option value="${esc(c)}" ${c===cat?'selected':''}>${esc(c)}</option>`).join('')}</select></div>`:''}<div class="rchart-body"><div class="rchart-ylabel">${esc(t(byPoints?'axisPoints':'axisRank'))}</div><div class="rchart-yaxis">${y.ticks.map(v=>`<span style="top:${yPct(v).toFixed(2)}%">${esc(byPoints?num.format(v):'#'+num.format(v))}</span>`).join('')}</div><div class="rchart-plot">${xt.map(ms=>`<i class="vgrid" style="left:${xPct(ms).toFixed(2)}%"></i>`).join('')}<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts.map(p=>`${p.x.toFixed(2)},${p.yy.toFixed(2)}`).join(' ')}" vector-effect="non-scaling-stroke"/></svg>${pts.map(p=>p.html).join('')}</div><div class="rchart-xaxis">${xt.map(ms=>`<span style="left:${xPct(ms).toFixed(2)}%">${esc(monthLabel(ms))}</span>`).join('')}</div></div><p class="source-note">${shown.length}/${series.length} ${esc(t('snapshotsShown'))} · ${esc(t('chartNote'))}</p></div>`;
}
function rankingSection(ranks){
 if(!ranks.length)return `<div class="section-header"><h3>${esc(t('rankHistory'))}</h3></div>${empty('noRankData')}`;
 return `<section class="white-panel rchart-panel">${rankingChart(ranks)}<details class="rtable"><summary>${esc(t('snapshots'))} · ${ranks.length}</summary>${dataTable(['date','category','rank','points','source'],ranks.map(r=>`<tr><td>${datefmt(r.date)}</td><td>${esc(r.category)}</td><td>#${r.rank}</td><td>${r.points==null?'—':esc(fmtPoints(r.points))}</td><td>${external(r.source_url,t('source'))}</td></tr>`))}</details></section>`;
}
// Each page names itself in the tab, the history and bookmarks.
function pageTitle(route){
 const named={event:eventById,player:playerById,club:clubById}[route.view];
 let name='404';
 if(named)name=(named.get(route.id)||{}).name||'404';
 else if(route.view==='h2h'){const pair=h2hIds(route).filter(Boolean).map(id=>getPlayer(id).name).join(' – ');name=pair?`${pair} · ${t('h2h')}`:t('h2h');}
 else if(['events','players','clubs','rankings','about'].includes(route.view)||(route.view==='feedback'&&feedbackOn()))name=t(route.view);
 else if(route.view==='home')return `${SITE_TITLE} — ${t('homeTitle')}`;
 return `${name} · ${SITE_TITLE}`;
}
function render(){document.documentElement.lang=state.lang;const route=hashRoute();document.title=pageTitle(route);if(route.view!=='feedback')fb.from=location.hash||'#home';if(prepareResults(route))return;const views={home:landing,events:eventsPage,players:playersPage,clubs:()=>rosterPage('clubs'),rankings:rankingsPage,h2h:h2hPage,about:aboutPage,...(feedbackOn()?{feedback:feedbackPage}:{})};const content=views[route.view]?views[route.view]():route.view==='event'?eventPage(route.id):route.view==='player'?playerPage(route.id):route.view==='club'?clubPage(route.id):notFound();app.innerHTML=header()+updateNotice()+content+footer();}
window.addEventListener('hashchange',()=>{state.page=0;state.phaseFilter='all';state.query='';state.season='all';state.type='all';state.withResults=true;state.eventTab='';state.eventPlayer='';state.eventCategory='all';state.profileKind='all';state.clubSeason='';state.rosterCat='';state.rosterSort='';state.rosterDate='';state.chartRange='all';state.chartCat='';state.h2hQuery1='';state.h2hQuery2='';if(fb.status==='sent')fb.status='idle';fb.error='';window.scrollTo({top:0,behavior:'auto'});render();});
function focusRerender(id){const el=document.getElementById(id);const start=el&&typeof el.selectionStart==='number'?el.selectionStart:undefined;render();const next=document.getElementById(id);if(next){next.focus();if(start!==undefined)next.setSelectionRange(start,start)}}
document.addEventListener('input',e=>{if(e.target.matches('#search-events,#search-roster,#search-rankings,#search-home')){state.page=0;state.query=e.target.value;focusRerender(e.target.id)}else if(e.target.matches('#h2h-search1,#h2h-search2')){state[e.target.id==='h2h-search1'?'h2hQuery1':'h2hQuery2']=e.target.value;focusRerender(e.target.id)}else if(e.target.matches('#fb-message,#fb-email,#fb-website')){fb[{'fb-message':'message','fb-email':'email','fb-website':'trap'}[e.target.id]]=e.target.value}});
// Enter in a head-to-head search picks the first athlete listed.
document.addEventListener('keydown',e=>{if(e.key!=='Enter'||!e.target.matches||!e.target.matches('#h2h-search1,#h2h-search2'))return;const first=e.target.parentElement&&e.target.parentElement.querySelector('.h2h-results a');if(first){e.preventDefault();location.hash=first.getAttribute('href');}});
document.addEventListener('submit',e=>{if(e.target.id==='feedback-form'){e.preventDefault();sendFeedback()}});
document.addEventListener('change',e=>{if(e.target.id==='fb-topic'){if(FEEDBACK_TOPICS.includes(e.target.value))fb.topic=e.target.value;return;}state.page=0;if(e.target.id==='phase-filter'){state.phaseFilter=e.target.value;render()}if(e.target.id==='ranking-date'){state.rankDate=e.target.value;render()}if(e.target.id==='season-filter'){state.season=e.target.value;render()}if(e.target.id==='type-filter'){state.type=e.target.value;render()}if(e.target.id==='results-only'){state.withResults=!!e.target.checked;render()}if(e.target.id==='event-category'){state.eventCategory=e.target.value;render()}if(e.target.id==='club-season'){state.clubSeason=e.target.value;render()}if(e.target.id==='roster-year'||e.target.id==='roster-month'){const cat=rosterCategory(),dates=snapshotDates(cat);const pick=e.target.id==='roster-month'?e.target.value:dates.find(d=>d.startsWith(e.target.value));if(pick){state.rosterCat=cat;state.rosterDate=pick===rankingIndex().latestDate.get(cat)?'':pick;render()}}if(e.target.id==='roster-sort'){state.rosterSort=e.target.value;render()}if(e.target.id==='chart-category'){state.chartCat=e.target.value;render()}if(e.target.id==='ranking-category'){state.rankCategory=e.target.value;state.rankDate='latest';render()}});
document.addEventListener('click',e=>{if((e.target.closest('#archive-reload')||e.target.closest('#archive-update'))){location.reload();return;}if(e.target.closest('#fb-again')){fb.status='idle';render();return;}if(e.target.closest('#page-prev')){state.page--;render()}if(e.target.closest('#roster-latest')){state.rosterDate='';state.page=0;render();return;}const rosterTabs=['all',...rankingIndex().cats];for(let i=0;i<rosterTabs.length;i++)if(e.target.closest('#roster-tab-'+i)){state.rosterCat=rosterTabs[i];state.rosterDate='';state.rosterSort='';state.page=0;render();return;}for(const k of ['standings','players','matches','doubles','fixtures'])if(e.target.closest('#tab-'+k)){state.eventTab=k;state.page=0;render();return;}for(const k of ['all','1y','6m','3m'])if(e.target.closest('#range-'+k)){state.chartRange=k;render();return;}for(const k of ['all','individual','team'])if(e.target.closest('#scope-'+k)){state.profileKind=k;state.page=0;render();return;}const kindChip=e.target.closest('[data-kind]');if(kindChip){state.type=kindChip.getAttribute('data-kind');state.page=0;render();return;}const pick=e.target.closest('[data-event-player]');if(pick){state.eventPlayer=pick.getAttribute('data-event-player');state.eventTab='matches';state.phaseFilter='all';state.page=0;render();window.scrollTo({top:0,behavior:'auto'});return;}if(e.target.closest('#page-next')){state.page++;render()}if(e.target.closest('#lang-switch')){state.lang=state.lang==='el'?'en':'el';try{localStorage.setItem('tt_lang',state.lang)}catch{}render()}});
render();
if(db.meta.partitions&&db.meta.release_id&&typeof setInterval==='function'){
 setInterval(checkForUpdate,5*60*1000);
 checkForUpdate();
}
})();
