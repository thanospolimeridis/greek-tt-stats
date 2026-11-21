# Resumable competition imports

`data/import-plan.json` freezes the public inventory and a **2026-11-20 result cutoff**. It queues **502 additional competitions**, alternating seasons: the original 481 past-dated competitions, 19 active leagues, and two undated listings requiring inspection. Eleven competitions had already been processed. Five future competitions remain deferred. The original scope is retained in `data/import-plan-finished-2026-11-20.json`, and the new plan records its hash. No previously queued event has been dropped. The legacy seed listing absent from TTScore's current catalog is not silently added to this queue.

The public catalog covers nine seasons, 2018–19 through 2026–27. Past dates establish eligibility for inspection, not proof that results are complete or that an event actually took place.

Active and undated events use the explicit `available_results` scope. Only results with valid source dates on or before the cutoff can enter the archive. Future fixtures are excluded before retrieving their match sheets, future individual results are excluded, and missing or inconsistent scores remain review records. These event snapshots always stay partial and retain the cutoff and whether the event was ongoing or undated. Undated event metadata is never replaced with an invented date. A new plan can opt into this scope with `--include-available`; that option refuses to silently alter an existing plan.

## Run or resume

```sh
# Process up to 18 new competitions, with a validated export after each event.
python3 scripts/batch_import.py --limit 18

# Continue the entire remaining queue.
python3 scripts/batch_import.py

# Prioritize an existing eligible competition, then continue the same full queue.
python3 scripts/batch_import.py --priority 782

# Re-normalize from the local source cache, without network access.
python3 scripts/batch_import.py --offline
```

The default reviewed baseline is `imports/`; the evolving validated bundle is `capture/batch-imports/`. Current status is in `capture/batch-state.json`. A fresh worker handles each event, validates its normalized records, and writes an adapter-versioned checkpoint to `capture/batch-checkpoints/`. The parent merges identities and validates the whole archive before replacing the prior staged export. Failed events are not marked imported; already completed exports survive an interruption.

A checkpoint may be reused only with the same adapter fingerprint. A changed adapter is replayed from cached source responses before its results are reused. Offline runs always re-normalize event source data; they do not rely on normalized checkpoints. Request throttling carries across worker restarts, and the collector remains sequential with at least one second between request starts.

Worker checkpoints also bind the cutoff and available-results scope. Release replay repeats those options, and the audit rejects future results or new rows in a still-deferred competition.

New competitions use `compact_brackets_v2`: valid singles scores are read directly from the public knockout/consolation bracket, and explicit singles byes can avoid empty detail pages. Existing competitions retain their recorded retrieval mode (`details` or `compact_brackets_v1`) and original per-record source evidence. The mode is saved in event coverage and worker checkpoints and repeated during offline replay. Adapter refreshes do not consume the `--limit` allowance for new competitions.

`--priority` changes processing order without changing the frozen eligible scope or dropping other competitions. It can be repeated. Coverage records the actual merge order, and release replay uses that order to preserve athlete names, aliases and source identity evidence exactly. Stop the existing collector at an event boundary before restarting with priorities; run only one online collector against a cache at a time.

For a graceful stop after the active event:

```sh
touch capture/pause-import
# Wait for capture/batch-state.json to report batch_finished.
# Remove that stop file when ready to continue, then repeat the command.
```

Interrupting earlier loses only normalization work for the current event; completed raw responses and validated events remain cached. Do not publish raw capture folders: participant responses may include unnecessary personal fields. Only allowlisted competition identity fields enter normalized CSVs.

The inventory fingerprint excludes inferred event type, so discovering a league does not invalidate the plan. Changes to public event identities, dates or names require review and a new plan. New source retrieval snapshots should use a separate cache; do not splice mutable responses into an old replay snapshot.

## Supported results and explicit gaps

- Event navigation selects individual group, knockout/consolation, league, or team-tournament adapters.
- Team tournament groups and brackets use their linked fixture score tables and the same publicly exposed team sheets as leagues. Aggregate fixture scores must agree with declared rubber winners.
- Individual records require consistent point scores, final set totals, source participant identities and legal match termination. Duplicate game IDs cannot change score, winner, event, or doubles membership.
- Identical group abbreviations can be resolved from the already captured group matrix only when explicit participant IDs, reciprocal final scores, standings win/loss totals and the complete single-round-robin schedule establish one unique assignment of every game to a distinct pair. Every point score and date must validate, registrations must be distinct, and all pairs must occur exactly once. Partial groups, repeated pairings, walkovers, conflicting matrices and remaining ties retain the identity-review gap. `matrix_identity_resolutions` counts recovered records; no fuzzy name matching or extra source requests are used.
- Walkovers, noncountable rubbers, unresolved identities, unknown layouts, missing results, and inconsistent scores remain explicit source issues. The importer never supplies fictional scores to fill them.
- A fixture whose two club labels are identical is kept as an identity-review gap until distinct team identities can be established from public evidence. Its independently valid player results are still imported when registration IDs, point scores and the aggregate sheet agree, retaining their source link without a fabricated fixture relationship. The coverage issue counts those recovered results. No invented club suffixes are created.
- The schedule-wide JSON feed was inspected but contains scheduling information rather than score evidence. Valid singles bracket scores use the compact adapter described below; other results retain explicit game-score tables.

`coverage.batch` records attempted and pending counts, pending event IDs, and deferred reasons. Each competition retains phase/category traversal, result counts, and issue counts. “Checked” does not mean a complete historical record. A competition with zero usable results stays visible in the coverage report.

## Fewer public requests

TTScore places a winning player's previous-match point scores in the next bracket column. Positive numbers give the loser's points in games won by that player; negative numbers give that player's points in games they lost. Both identities, the current match's winner flag, the next-column participant, a valid date and a legal completed match must agree. Deuce points and negative zero are preserved. Every decoded result passes the same point-score, set-total and termination validator as an explicit score table.

The score adapter only skips a detail request for a unique single-game group with two resolved singles participants. Team matches, doubles, walkovers, missing dates, conflicting bindings, malformed scores and unknown layouts fall back to the existing detail importer. Compact results cite the original bracket response hash and public bracket URL; no synthetic source response is generated. `compact_bracket_matches` records how many detail requests were avoided, without changing any completeness claim.

Version 2 also skips a unique singles group explicitly marked `ko-bye`, with exactly one identified advancing player and no contradictory identity or winner flag on the bye side. It creates no match, win, loss or fictional score. Blank positions, double byes, team/doubles entries and ambiguous brackets retain detail retrieval. `explicit_bracket_byes` records these exclusions against the captured bracket evidence. In an offline comparison, all 1,900 conservatively identified bye groups had empty detail tables; no contradictory results were found.

The initial offline comparison covered 403 bracket pages: 7,214 decoded results exactly matched their cached detail records, including dates and every point score. Two invalid compact results correctly required fallback. This would avoid about 52% of the 13,860 captured source requests in that sample before the bye optimization; actual speed depends on competition format. Full-event comparisons for events 462, 551 and 898 preserved all normalized identities, scores and review issues. Event 898 needed 114 requests instead of 328 with version 1, and 87 with version 2. The one-request-per-second limit is unchanged.

Repeat the comparison against available private cache evidence:

```sh
python3 scripts/benchmark_brackets.py --input capture/batch-imports/provenance.json
```

The benchmark is offline and fails on differences. A public all-seasons export has not been found; an authorized federation/TTScore export could remove more requests and help establish coverage of unlisted events.

## Validate and stage a release

```sh
python3 scripts/import_csv.py --input capture/batch-imports --output /tmp/ttscore-batch-catalog.json
python3 scripts/validate_batch.py --cache capture/ttscore --replay --output capture/release-audit.json
python3 -m unittest discover -s tests -v
node tests/smoke.js
```

The release audit rejects lost or changed baseline records, incomplete queue traversal, misleading event totals, and changed source evidence. `--replay` normalizes source responses again in offline workers and requires byte-identical CSVs and full provenance. It merges once at the end, avoiding repeated large archive writes during release checks. Use `--allow-pending` only to inspect or publish an explicitly partial checkpoint. Preserve the original baseline when promoting a release, and pass it with `--baseline PATH` to repeat preservation and replay checks afterward.

Review preservation of the existing archive and source issues before copying staged CSVs and `provenance.json` into `imports/`. Rebuild with `scripts/import_csv.py` and `scripts/build.py`, then commit and push to `develop`; the public site changes only with a release. Neither GitHub Actions nor ordinary site builds contact TTScore.

For repeated updates while collection is running, use the release helper with the original baseline:

```sh
python3 scripts/release_batch.py --baseline capture/batch-baseline --allow-pending --promote
python3 scripts/import_csv.py
python3 scripts/build.py
python3 -m unittest discover -s tests -v
node tests/smoke.js
```

The helper freezes one complete checkpoint under `capture/releases/`, checking CSV hashes and rejecting a mixed export if collection advances during the copy. It verifies the original baseline, every referenced raw response, and a fresh offline replay before updating `imports/` and README coverage. Omitting `--promote` performs the audit without changing published inputs. Only the seven normalized CSVs and provenance are copied; unrelated files and raw responses cannot enter a release. Rebuild, test, commit and push to `develop` after promotion, then check the validation workflow. Keep the original baseline unchanged throughout the batch. This helper makes no network requests and does not schedule future work.

## Refresh cycles

The archive plan above checks every competition once. While a season is running, `scripts/refresh.py` adds a cycle on top of it:

```sh
python3 scripts/refresh.py                       # what a refresh would queue; makes no requests
python3 scripts/refresh.py run                   # one cycle through yesterday, staged on develop
python3 scripts/refresh.py run --as-of 2026-11-29 --no-stage
python3 scripts/refresh.py rehearse              # the whole cycle offline in a scratch folder
```

One cycle, in order:

1. **Listing.** The public catalog is read again. New competitions are added and changed listing fields (dates, names) are taken over; both are recorded in the plan as `catalog_changes`. A competition that is no longer listed stops the refresh for review.
2. **Plan.** `data/import-plan.json` is replaced by a refresh plan (`kind: refresh`, `schema_version: 3`) that records the hash of the plan before it. It queues competitions that were open at their last check and ones never checked that have started. One that has finished since gets a complete check in place of its partial snapshot. Competitions already checked as finished are never queued again, and an undated listing from an earlier season is left alone. Listings that have not started are deferred.
3. **Results.** The queue is collected by `batch_import.py` into the cycle's own cache folder, `capture/refresh/<cutoff>/cache`. The first cache, `capture/ttscore`, and the caches of earlier cycles are never written to, so a page fetched again does not overwrite the response that earlier results cite.
4. **Audit and replay.** The release helper runs as for any batch, with every cache folder listed. It replays the cycle's competitions offline and requires byte-identical CSVs and provenance. The listing step is replayed from the cycle cache as well.
5. **Rankings and standings.** New official ranking snapshots are added to `imports/ranking-history/`. The standings of the leagues the cycle checked are read again from the pages it already fetched (`import_standings.py --update`), so tables and fixtures show the same day and no extra requests are made.
6. **Staging.** The site is rebuilt twice for the determinism check, both test suites run, and the changed inputs are committed and pushed to `develop` as `HEAD:develop`. The cycle then waits for the validation workflow. Nothing is published; that is a release (README, "Releases and versions").

The default cutoff is yesterday in Athens. Results entered during a match day can still be incomplete at the source, and a half-entered team fixture can look like a finished one.

### What a refresh may change

Nothing published may be lost or altered. The audit allows three exceptions, each named by the frozen plan:

- **Listing fields** in `catalog_changes`.
- **Source evidence retrieved again during the cycle.** A request made again replaces its earlier record only when the request is identical and its retrieval time is not before the plan's `created_at`.
- **Results a reviewer let follow the source**, listed by record ID under `accepted_source_changes`.

If the source has changed a published result, or no longer shows one, the collector stops and names the records. Compare them with the source. To accept the source's version, add their IDs to `accepted_source_changes` in `data/import-plan.json` and run the same command again: the listed records are then replaced or removed, and the audit lets exactly those through.

### Fewer requests

A competition checked again asks for the sheet of every fixture. The sheets behind fixtures the archive already publishes are copied into the cycle's cache with their original retrieval record, so a weekly refresh costs the listing pages plus the new fixtures. A correction the source makes later to an old sheet is not seen this way; `--recheck-sheets` fetches every sheet again. A fixture whose listed score no longer matches its carried-forward sheet fails the usual cross-check, its published rows drop out of the worker's result, and the refresh stops as described above.

### Resuming and disk use

Run the same command again to resume: finished competitions are kept, and every later step can be repeated safely. `touch capture/pause-import` stops the collector before its next competition. Source or network outages are retried (`--retries`, `--retry-wait`).

A staged cycle keeps its evidence in `capture/refresh/<cutoff>/`: the cache, the plan, the audit report and the log. The baseline, the staged archive and the checkpoints are deleted, since Git history and an offline replay can produce them again.

`rehearse` runs a whole cycle offline in `capture/refresh-rehearsal/`, with the newest cached responses standing in for the source, and compares the result with `imports/`: all seven tables must come out byte for byte the same. It changes nothing in the repository. Run it after touching the refresh or the collector.

## Unattended collection

`scripts/continue_archive.py` runs a large archive queue unattended; for the weekly refresh use the cycle above. It collects a batch of competitions, stops at an event boundary, and stages that batch with the release helper above. Staging includes the rebuild, both test suites, a determinism check, the commit, the push to `develop` and a wait for the validation workflow. It then starts the next batch. It starts only from a checkout that is exactly at `origin/develop`, and it never publishes.

```sh
python3 scripts/continue_archive.py --batch 50 --detach   # background, under caffeinate
tail -f capture/supervisor.log capture/batch-progress.log
touch capture/pause-import       # stop after the current competition
```

How it handles problems:

- **Outages:** TTScore outages and network failures (HTTP 429/5xx, timeouts, dropped connections) are retried after `--retry-wait` minutes. It stops after `--max-retries` consecutive failures that make no progress. Validated events from an interrupted batch are staged at the next clean batch boundary.
- **Everything else stops for review:** validation errors, corrupt cache entries, robots.txt or redirect refusals and a failed validation workflow. Status is in `capture/supervisor-state.json`.
- **No double runs:** it adopts a collector that is already running instead of starting a second one, and it refuses to run beside another supervisor.

Restarting after `pause-import` stages any validated competitions that are not yet staged, then continues. The supervisor is not part of the adapter fingerprint, so editing it never re-normalizes checked events. Edits to the six adapter files do. Make those only at a release boundary.

The website paginates long player histories and coverage tables. Hosted detail views load content-addressed static JSON for the selected event, player, or club; H2H uses the complete selected player's history. Missing downloads show a retry message, never an empty-history claim. Detailed request provenance is downloadable as `provenance.json`; `coverage.json` exposes coverage and exclusions. The complete portable page remains available as `index.html` in local builds and `offline.html` on the hosted site. It retains coverage, source links, and all statistical records without duplicating the full request log.

Hosted pages check a small static release marker every five minutes and offer “Load update” when a newer archive is published. They preserve the current page until the visitor chooses to load it. The portable HTML remains self-contained.
