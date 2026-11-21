# Greek TT Archive · Ελληνική Επιτραπέζια Αντισφαίριση

Free, open-source Greek table tennis statistics: **Python ingestion + a static, offline-ready website**. No database server, paid APIs, subscriptions or frontend dependencies. Independent project, not an official ΕΦΟΕπΑ service.

## Current coverage — 21 November 2026

- **518 publicly listed TTScore events**, reconciled across 2018–19 through 2026–27.
- **1 additional legacy event** retained from the original prototype, labelled absent from the current catalog (519 displayed total).
- **88,852 completed singles matches, 3,143 doubles matches and 8,824 team fixtures**, from 496 competitions across all nine listed seasons.
- **3,499 athletes**, linked by federation registration number where available, and **191 exact club names**.
- **332,624 official ranking records**: 12 age categories, 79 snapshot dates from 15 September 2018 to 1 October 2026.
- **1,401 doubles matches identify all four members**; 1,742 preserve source pair labels without invented athlete links.
- **5,417 source issues** are recorded, including walkovers, unresolved fixtures and inconsistent scores. Coverage reports retain exclusion reasons and unplayed/bye counts.
- The current resumable batch has checked **502 of 502 additional eligible competitions**. **0 remain queued**, and 5 listings remain explicitly deferred; the coverage report gives their reasons. Results from active or undated events are limited to explicit, validated scores dated on or before 20 November 2026 and remain partial snapshots.

**Historical results are incomplete.** The eligible competition queue has been checked; source gaps and deferred listings remain. The season-by-season table on About shows the exact scope. No results are invented. Validation checks source consistency, not independent historical truth. The About page exposes scope and exclusions, with downloadable coverage and provenance reports.

## Use and build

Build from the committed CSVs, then open `index.html` directly or serve the folder with `python3 -m http.server 8000`. The generated portable site works offline; source links require Internet access. A ready-built portable copy is also available as [offline.html](https://thanospolimeridis.github.io/greek-tt-stats/offline.html).

```sh
python3 scripts/import_csv.py
python3 scripts/build.py
python3 -m unittest discover -s tests -v
node tests/smoke.js
```

Python 3.10+ is sufficient for ingestion/build. Node is only needed for the zero-dependency frontend tests (CI uses Python 3.12 and Node 22). Builds do not contact TTScore.

Implemented views: Greek/English navigation, accent-insensitive Greek and transliterated/alias search, one competitions list for tournaments and leagues (type taken from the source's own result views, never guessed from names), competition pages with per-player summaries, match cards, phase/category filters, doubles and team fixtures, league standings as the source publishes them (wins, losses, Disq and points per team; teams level on points share a position because the source gives no tie-break order), player profiles split by individual/team competitions with per-season tables, a match breakdown (score lines, final-game record, record by the opponent's official ranking position on the match day, best wins, most-played opponents), official ranking points over time across age categories, game-by-game histories, H2H, ranking snapshot selection, and club pages by season (league positions as the source publishes them, who played team matches for the club, fixtures from the club's side, and the roster in official ranking order). Original names and category labels retain their source language. Player club labels are dated ranking observations, not inferred current membership.

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

New work is staged on `develop`. Commit and push there: the validation workflow runs, and nothing is published. `main` is the public site, so it moves only when a release is wanted, and only to a numbered release (see [Releases and versions](#releases-and-versions)):

```
python3 scripts/release.py patch
PUBLISH=1 git push --atomic origin develop develop:main vX.Y.Z
```

The first command cuts the release on `develop` and prints the second, which fast-forwards `main` to it, sends its tag and starts the deployment. If Git rejects the push as non-fast-forward, `main` holds commits that `develop` lacks; the release script checks for that before it tags anything.

`scripts/hooks/pre-push` guards this. It refuses any push to `main` that is not made with `PUBLISH=1`, and any push whose commit is not a release: the tag `vX.Y.Z` named by that commit's `VERSION` has to point at it, and has to be in the push or already on the remote. A hook is local to a clone, so install it once per clone (its worktrees share it):

```
cp scripts/hooks/pre-push "$(git rev-parse --git-common-dir)/hooks/pre-push"
```

The unattended collector (`scripts/continue_archive.py`) predates both staging and releases: it must run on `main` and pushes each finished batch there itself, with no release. The guard refuses those pushes, with or without `PUBLISH=1`, so the collector has to be adapted to stage its batches on `develop` before it is run again.

GitHub Pages supports public repositories on GitHub Free: [official documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages). Use the default `github.io` address; no purchased domain is required. The application has no hosted backend or recurring service dependency.

## Releases and versions

Every public state of the site is a numbered release. `VERSION` holds the number as `MAJOR.MINOR.PATCH` and is the only place it is set. The build stamps it into both pages and into `version.json`; the footer shows it, linked to [`CHANGELOG.md`](CHANGELOG.md); and a copy of the site left open names the newer release once one is published. The number identifies a release of the site. It says nothing about how complete the data are, and `dataset_sha256` remains the identity of the data.

| Part | Raised for |
| --- | --- |
| `patch` | Fixes, wording, and refreshes of data that were already covered |
| `minor` | New features, and newly covered competitions, seasons or tables |
| `major` | Redesigns, and changes that break saved links or the published file formats |

Branches and commits on `develop` leave `VERSION` and `CHANGELOG.md` alone, so parallel work never conflicts over them. A release is cut on `develop` when one is wanted:

```sh
python3 scripts/release.py          # the current version and the commits waiting since the last release
python3 scripts/release.py minor    # or patch, major, or a version named outright such as 1.0.0
```

The script refuses unless the checkout is on `develop`, has no uncommitted changes and already contains `origin/develop` and `origin/main`. It then raises `VERSION`, adds a `CHANGELOG.md` section listing the subject of every commit since the previous release, commits the two files as `Release X.Y.Z` and tags that commit `vX.Y.Z`. Nothing is pushed: it prints the publishing command and stops. Until that command is run the release can be withdrawn by deleting the tag and the commit.

Because every release is tagged, an earlier one can be put back on the public site. The guard allows it, since the commit is a release:

```sh
PUBLISH=1 git push --force origin 'vX.Y.Z^{commit}:main'
```

`develop` keeps the later work, and the next release moves `main` forward again.

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
| `imports/ranking-history/` | Official ranking snapshots (yearly CSV shards) with their own provenance; never read or written by the batch collector |
| `scripts/import_rankings.py` | Adds ranking snapshots to `imports/ranking-history/` (`--offline` replays the cache) |
| `scripts/ranking_history.py` | Validates the ranking history and merges it at build time |
| `imports/standings/` | League standings as TTScore publishes them, with their own provenance; never read or written by the batch collector |
| `scripts/import_standings.py` | Rebuilds `imports/standings/` from the league overview pages (`--offline` replays a cache) |
| `scripts/standings.py` | Reads the source's standings tables, validates the folder and adds it at build time |
| `data/verified_events.json` | Original prototype's seed listings; not evidence of complete coverage |
| `tests/` | Synthetic parser/validation regressions and frontend behavior checks |
| `docs/` | Audit, observed source schema and remaining work |
| `.github/workflows/` | Validation and free static deployment |
| `scripts/hooks/pre-push` | Local guard that refuses pushes to `main` made without `PUBLISH=1` or of a commit that is not a tagged release |
| `VERSION`, `CHANGELOG.md` | The site's release number and what each release changed; written only by `scripts/release.py` |
| `scripts/release.py` | Cuts a release on `develop`: raises `VERSION`, extends `CHANGELOG.md`, commits and tags |

The hosted site loads result files for the selected player, competition, or club. Whole-archive totals remain visible, and failed downloads are explicitly distinguished from empty histories. Player histories and coverage tables are paginated; the full request manifest is downloaded separately. The build also produces a complete, self-contained `index.html` for offline use, published as `offline.html` from the About page. No server or frontend dependency is needed for either version. Ranking rows are stored compactly in the site (snapshot date, category and source once per snapshot); each player's file carries their ranking history and each past snapshot date has its own file. Remaining work includes unchecked competitions, unresolved source issues, richer nonplayed outcomes and resolved tournament-doubles identities. Do not label those gaps complete.

## Licence

Site code is MIT licensed. This grants **no licence to third-party TTScore/federation data**. Public accessibility does not itself settle bulk republication rights. Retain attribution and honor corrections/removal requests. No exact birth dates, birth years, contact details, or unnecessary personal fields are published by this importer.
