# TTScore public extraction notes

The historical group, knockout, consolation and doubles adapters are now implemented. See [Historical backfill](HISTORICAL_IMPORT.md) for current scope and replay commands. The initial discovery notes below explain the source contracts.

Observed on 2026-11-20 from [customer 24](https://app.ttscore.io/customer/24), without authentication. These are the site's own UI requests, **not a documented or guaranteed API**. They can change.

## Working retrieval path

| Purpose | Public UI request | Evidence and handling |
| --- | --- | --- |
| Season selector | GET `/customer_events.php?customer=24` | `select-season` lists nine seasons, 2018–19 through 2026–27 |
| Events | POST `/customer_events.php`: `customer=24`, `season=<selector value>`, `getStats=1` | Empty season means All. Reconcile union of all season IDs against All. 518 IDs matched |
| League categories | GET `/tournament_groups_league.php?event=777&customer=24` | `agecategoryid_league`; select values are discovered, never enumerated |
| League groups | POST same PHP path: `event`, `customer`, `getStats=1`, `agecategoryid_league` | Follow `loadSchedule(group,…)` IDs in returned markup |
| League standings | The same overview response | `div.groups[data-id]` table per group: `#`, Participant (`CLUB - TEAM`), Wins, Lost, Disq, Pts. `#` is a draw slot, not a rank; no tie-break order is published; Disq is sometimes counted inside Lost and sometimes not, so Pts is kept as published. `X - X - BYE` rows are empty draw slots. Kept in `imports/standings/` by `scripts/import_standings.py`, outside the collector |
| Fixture list | GET `/tournament_groups_league.php?group=214221&customer=24` | `tr#game-ID` contains round, date, names and aggregate score |
| Match sheet | GET `/game-team.php?game=244051&customer=24` | Public dialog exposes its own JSON request |
| Individual rubbers | GET `/admin/ajax/team_games.php?game=244051&customer=24` | Public, unauthenticated endpoint despite the `/admin/` path; used by the public sheet. Contains `team_games`, player AM registration numbers, seven possible game scores, `Winner`, `Countable`, `Winsets`, `Score` |
| Individual groups | GET event navigation then POST `/rounds_schedule2.php`: `event`, `customer=24`, `getStats=1`, `agecategoryid_groups` | Follow linked groups and every `nextPage` link; GET the explicit `group` score table |
| Knockout / consolation | POST `/tournament_ko_games.php`: `event`, `customer=24`, `getStats=1`, `agecategoryid_ko`, `series=1` or `2` | Bind bracket game IDs and participant IDs; decode verified winner-relative singles point notation, falling back to explicit group-score tables when unresolved; see [request reduction](BATCH_IMPORT.md#fewer-public-requests) |
| Tournament participants | POST `/tournament_players.php`: `event`, `customer=24`, `getStats=1`, `agecategoryid_players` | Public JSON supplies participant ID, AM and full name. Emit only allowlisted identity fields; raw payload includes unnecessary personal fields |
| Ranking selector | GET `/customer_ranking.php?customer=24` | Discover `agecategoryid` and `select-date` options |
| Ranking snapshot | POST same PHP path: `customer=24`, `getStats=1`, `agecategoryid`, `select-date` | Latest option is **0**, not its displayed ISO date. Resolve the displayed date into provenance. Earlier dates use their literal option values |

The latest selector displayed 2026-10-01. Sending that date literally instead of `0` returned an invalid placeholder row; the importer rejects this rather than manufacturing a snapshot. Historical 2026-08-01 returned valid rows. The source has two 1970-01-01 event placeholders; those normalize to unknown dates, retaining raw source evidence in the local cache.

## Identity and outcome rules

- Canonical player ID is `httf-<AM/RN>` when a positive registration number exists. Names never establish identity. Missing registration numbers use `ttscore-local-<event>-<participant ID>` and do not merge across events.
- Different spellings attached to the same registration number become aliases. The earliest imported spelling remains the display name.
- Club IDs hash exact normalized source names (`club-name-…`). This is explicitly provisional: two spellings can represent one club. No fuzzy merging occurs. Reviewed corrections with evidence are applied at build time from `data/identity-corrections.json` (see README, Identity corrections); the collector never merges.
- Player `club_id` is the latest **imported ranking observation**, with `club_as_of`; it is not a claim about present-day membership. Historical matches preserve their own club IDs.
- Completed singles require positive participant IDs, a declared winner, countable result, consistent final set totals and legal game scores. Unplayed lineup slots produce no fabricated matches.
- Doubles are stored separately, with resolved team members or explicitly unresolved tournament pair labels. Noncountable/walkover records and inconsistent source rows require review. Review IDs and source hashes are listed in the manifest. Doubles count when reconciling a sourced team fixture, but not in singles/H2H statistics.
- Team fixture aggregate scores are cross-checked against all declared rubber winners before import. A disagreement is reported and that fixture is excluded.
- Event state “Finished” does not prove result completeness. Catalog, fixture traversal and individual-result coverage remain separate.

## Reproduce this snapshot

Normal builds are completely offline and use committed CSVs:

```sh
python3 scripts/import_csv.py
python3 scripts/build.py
```

Original catalog/league/ranking collection and cache replay, staged separately so historical additions are preserved:

```sh
python3 scripts/ttscore.py --output /tmp/ttscore-base --league 777 \
  --ranking 15:2026-08-01 --ranking 10:2026-08-01 \
  --ranking 15:latest --ranking 10:latest

# Same request selection, using only existing hash-verified local responses:
python3 scripts/ttscore.py --offline --output /tmp/ttscore-base --league 777 \
  --ranking 15:2026-08-01 --ranking 10:2026-08-01 \
  --ranking 15:latest --ranking 10:latest
```

For the expanded archive, use the [historical replay command](HISTORICAL_IMPORT.md), which merges the existing archive. The base collector above always includes the catalog. Repeating `--league` and `--ranking` selects additional supported batches. Output is a **replacement snapshot of the selected scope**, not an incremental merge: repeat all desired selections. An existing manual CSV directory without a provenance manifest is protected from overwrite. Use `--output /tmp/ttscore-review` to stage another scope.

The default cache is `capture/ttscore/` (Git-ignored). Cached requests are immutable; no automatic freshness claim is made. Use `--cache capture/ttscore-YYYY-MM-DD` for a new retrieval snapshot. The latest ranking option is pinned by its cached selector, so never copy selected cache files between generations.

`imports/provenance.json` links each request to response hash and retrieval time and hashes every emitted CSV. All staging files are validated before promotion; the manifest detects an interrupted or mixed promotion. The canonical JSON and HTML are deterministic. A fresh clone can reproduce the site from CSV; exact **raw-response replay** needs the private local cache. Request metadata and hashes alone cannot recover a changed remote response.

The network client limits requests to one/second (or slower), checks robots rules, stops on unexpected redirects/authorization failures, bounds response size, retries transient HTTP errors, and fails on cache corruption. A server asking for a retry delay over 60 seconds stops the run for a later retry. Requests never include credentials or browser sessions.

## Best path to a complete historical archive

1. Keep a versioned inventory of public events per season; reconcile with All on each new snapshot. Ask the federation/TTScore for an authorized bulk export or authoritative event inventory if one is available. That is the strongest way to establish coverage of deleted/unlisted events; no such export was discovered in this audit.
2. Discover each event's own navigation. Leagues, groups, knockouts and consolation have different page formats. Do not assume every event is a league.
3. Extend the implemented and fixture-tested group/knockout adapters to remaining event formats. The public event 819 links `rounds_schedule2.php`, `tournament_ko_games.php?series=1`, and `series=2`. Group POST selects `agecategoryid_groups`; follow returned group IDs and every `nextPage` link. Group score rows carry stable game IDs but abbreviated participant names, so resolve identities through linked player records before import.
4. Public `player.php?event=819&player=47452&team=0&customer=24` exposes R.N, full name, club and event history. Use R.N and unique event participant mappings; never merge athletes across events using names. Its match-history rows alone lack stable game IDs and are unsuitable as the only deduplication source.
5. Doubles now have a separate result table; resolve remaining tournament pair identities only with source evidence; retain separate team fixtures and individual rubbers. Add explicit walkover/retirement adapters after verifying source semantics.
6. Traverse supported historical competitions in resumable, bounded batches. Reconcile discovered categories, groups, pages, fixture totals, unique game IDs, excluded rows and imported rows per event. Scheduled/pending records must never be labelled completed.
7. Iterate all advertised ranking dates/categories with the same snapshot parser, retaining failures and category-specific coverage.
8. Require explicit coverage evidence before upgrading an event to complete. The current adapter never asserts historical completeness.

The ordinary GitHub build deliberately makes no TTScore requests. There is no unverified scheduled bulk synchronization.
