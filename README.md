# Greek TT Archive · Ελληνική Επιτραπέζια Αντισφαίριση

Free, open-source Greek table tennis statistics: **Python ingestion + a static, offline-ready website**. No database server, paid APIs, subscriptions or frontend dependencies. Independent project, not an official ΕΦΟΕπΑ service.

## Current coverage — 21 November 2026

- **518 publicly listed TTScore events**, reconciled across 2018–19 through 2026–27.
- **1 additional legacy event** retained from the original prototype, labelled absent from the current catalog (519 displayed total).
- **55,644 completed singles matches, 1,020 doubles matches and 3,192 team fixtures**, from 286 competitions across all nine listed seasons.
- **3,225 athletes**, linked by federation registration number where available, and **181 exact club names**.
- **4,909 ranking records**: men and women, 1 August and 1 October 2026.
- **441 doubles matches identify all four members**; 579 preserve source pair labels without invented athlete links.
- **4,212 source issues** are recorded, including walkovers, unresolved fixtures and inconsistent scores. Coverage reports retain exclusion reasons and unplayed/bye counts.
- The current resumable batch has checked **288 of 502 additional eligible competitions**. **214 remain queued**, and 5 listings remain explicitly deferred; the coverage report gives their reasons. Results from active or undated events are limited to explicit, validated scores dated on or before 20 November 2026 and remain partial snapshots.

**Historical results are incomplete.** Collection continues through the remaining queue, with validated checkpoints published periodically. Additional ranking snapshots also remain unimported. The season-by-season table on About shows the exact scope. No results are invented. Validation checks source consistency, not independent historical truth. The About page exposes scope and exclusions, with downloadable coverage and provenance reports.

## Use and build

Build from the committed CSVs, then open `index.html` directly or serve the folder with `python3 -m http.server 8000`. The generated portable site works offline; source links require Internet access. A ready-built portable copy is also available as [offline.html](https://thanospolimeridis.github.io/greek-tt-stats/offline.html).

```sh
python3 scripts/import_csv.py
python3 scripts/build.py
python3 -m unittest discover -s tests -v
node tests/smoke.js
```

Python 3.10+ is sufficient for ingestion/build. Node is only needed for the zero-dependency frontend tests (CI uses Python 3.12 and Node 22). Builds do not contact TTScore.

Implemented views: Greek/English navigation, accent-insensitive Greek and transliterated/alias search, player profiles, game-by-game histories, H2H, ranking snapshot selection/history, tournament results with phase filters, separate doubles histories, and club fixture statistics. Original names and category labels retain their source language. Player club labels are dated ranking observations, not inferred current membership.

## Data pipeline

```text
Public TTScore UI requests → ignored raw response cache
                           → validated imports/*.csv + provenance.json
                           → data/catalog.json → portable index.html
                                               → dist/index.html + static result JSON
                           → GitHub Pages
```

Reproduce the original catalog/league/ranking scope in a **separate output directory** (the base collector replaces its output; it does not merge historical tournaments):

```sh
python3 scripts/ttscore.py --output /tmp/ttscore-base --league 777 \
  --ranking 15:2026-08-01 --ranking 10:2026-08-01 \
  --ranking 15:latest --ranking 10:latest
```

Add `--offline` to replay cached responses without network access. Use a **new `--cache` directory** for fresh retrievals. Output replaces the selected scope; repeat all desired league/ranking selections. Use `--output /tmp/ttscore-review` to stage new work. The importer refuses to overwrite manual CSV directories without its manifest.

Continue the frozen queue of all remaining eligible competitions in resumable batches:

```sh
python3 scripts/batch_import.py --limit 9
# Or process every remaining eligible competition:
python3 scripts/batch_import.py
```

The default output is `capture/batch-imports/`; completed competitions and raw responses are checkpointed separately. Use `--offline` to repeat normalization without network access. Review staged CSVs and coverage before promoting them to `imports/` and rebuilding. See [Resumable competition imports](docs/BATCH_IMPORT.md) for the frozen scope, pause/resume commands, and release checks; [Historical backfill](docs/HISTORICAL_IMPORT.md), [the audit](docs/AUDIT.md), and [TTScore extraction guide](docs/TTSCORE.md) document the original exploration and source contracts.

## Validation and provenance

`imports/provenance.json` retains request URL/method/form, retrieval UTC time, response SHA-256, CSV hashes, coverage and review records. Individual source IDs join to that manifest. Raw responses stay in Git-ignored `capture/`; birth years, nationality, contact information and registration notes are not emitted into normalized player records.

The validator rejects duplicate IDs/snapshots, missing references, malformed CSVs, unsafe source URLs, invalid dates, impossible completed game scores, score/winner disagreement, games after a match ends, and changed CSVs with stale provenance. The source importer also reconciles team scores with match sheets. `best_of` defaults to 5; set it explicitly for other match formats. Only `completed` singles count in H2H and win rates; noncompleted CSV records remain visible in histories.

Code changes preserve stable dataset bytes when data are unchanged. CI runs `python3 scripts/check_reproducible_build.py`, building twice from the committed CSVs and requiring byte-identical canonical JSON, portable HTML, hosted result files, coverage, provenance and release markers. Generated `data/catalog.json`, `index.html` and `dist/` stay out of Git to avoid storing growing duplicate copies of the archive. GitHub Pages builds and publishes them from the versioned source inputs. To correct source-derived records, update the adapter/source evidence and regenerate the manifest, rather than silently editing generated CSVs.

## Manual/authorized imports

Templates in `imports/*.csv.template` document the supported tables. For separate authorized CSVs use a separate directory and `python3 scripts/import_csv.py --input PATH`. Events, players, clubs, singles matches, doubles matches, official rankings and team fixtures are separate tables. Matches can reference `fixture_id` and historical `club1_id`/`club2_id`. Every match and fixture requires a source URL. No synthetic/test records belong in production CSVs.

Names alone never justify merging athletes. Club IDs based on names remain provisional until official club identity data are available. Maintain correction evidence and review renames explicitly.

## GitHub and free deployment

[Source repository](https://github.com/thanospolimeridis/greek-tt-stats) · [Configured website](https://thanospolimeridis.github.io/greek-tt-stats/)

The repository includes PR validation and a Pages deployment workflow. Pushes to `main` validate the committed source data, build `dist/`, and deploy. No TTScore secrets or service credentials are required by Actions.

GitHub Pages supports public repositories on GitHub Free: [official documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages). Use the default `github.io` address; no purchased domain is required. The application has no hosted backend or recurring service dependency.

## Project structure

| Path | Purpose |
| --- | --- |
| `scripts/ttscore.py` | Public request collector, source parsers and offline replay |
| `scripts/historical.py` | Resumable group, knockout, consolation and doubles imports |
| `scripts/batch_import.py` | Season-balanced queue, event checkpoints and validated staged exports |
| `scripts/validate_batch.py` | Baseline preservation, coverage reconciliation and source-cache audit |
| `scripts/release_batch.py` | Consistent checkpoint snapshots, offline release audits and promotion |
| `data/import-plan.json` | Frozen remaining competition queue and deferred listings |
| `data/backfill-plan.json` | Reviewed tournament selection across all nine listed seasons |
| `scripts/import_csv.py` | Validation and deterministic canonical dataset |
| `scripts/build.py` | Portable HTML plus hosted pages with static result files |
| `src/` | Greek/English static application |
| `imports/` | Normalized source CSVs and provenance manifest |
| `data/verified_events.json` | Original prototype's seed listings; not evidence of complete coverage |
| `tests/` | Synthetic parser/validation regressions and frontend behavior checks |
| `docs/` | Audit, observed source schema and remaining work |
| `.github/workflows/` | Validation and free static deployment |

The hosted site loads result files for the selected player, competition, or club. Whole-archive totals remain visible, and failed downloads are explicitly distinguished from empty histories. Player histories and coverage tables are paginated; the full request manifest is downloaded separately. The build also produces a complete, self-contained `index.html` for offline use, published as `offline.html` from the About page. No server or frontend dependency is needed for either version. Remaining work includes unchecked competitions, unresolved source issues, richer nonplayed outcomes, older ranking snapshots and resolved tournament-doubles identities. Do not label those gaps complete.

## Licence

Site code is MIT licensed. This grants **no licence to third-party TTScore/federation data**. Public accessibility does not itself settle bulk republication rights. Retain attribution and honor corrections/removal requests. No exact birth dates, birth years, contact details, or unnecessary personal fields are published by this importer.
