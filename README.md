# Greek TT Archive · Ελληνική Επιτραπέζια Αντισφαίριση

Free, open-source Greek table tennis statistics: **Python ingestion + a static, offline-ready website**. No database server, paid APIs, subscriptions or frontend dependencies. Independent project, not an official ΕΦΟΕπΑ service.

## Current coverage — 20 November 2026

- **518 publicly listed TTScore events**, reconciled across 2018–19 through 2026–27.
- **One additional legacy event** retained from the original prototype, labelled absent from the current catalog (519 displayed total).
- **260 completed singles matches and 56 team fixtures** from A1 men 2025–26, event 777.
- **2,483 athletes**, linked by federation registration number where available, and **138 exact club names**.
- **4,909 ranking records**: men and women, 1 August and 1 October 2026.
- Four doubles results are excluded from singles statistics and listed for review; 128 unplayed lineup slots are not results.

**Historical results are incomplete.** Other events, age categories and ranking dates are not yet imported. No results are invented. Validation checks source consistency, not independent historical truth. The About page exposes scope and exclusions.

## Use and build

Open `index.html` directly, or serve the folder with `python3 -m http.server 8000`. The site works offline; source links require Internet access.

```sh
python3 scripts/import_csv.py
python3 scripts/build.py
python3 -m unittest discover -s tests -v
node tests/smoke.js
```

Python 3.10+ is sufficient for ingestion/build. Node is only needed for the zero-dependency frontend tests (CI uses Python 3.12 and Node 22). Builds do not contact TTScore.

Implemented views: Greek/English navigation, accent-insensitive Greek and transliterated/alias search, player profiles, game-by-game histories, H2H, ranking snapshot selection/history, tournament results, and club fixture statistics. Original names and category labels retain their source language. Player club labels are dated ranking observations, not inferred current membership.

## Data pipeline

```text
Public TTScore UI requests → ignored raw response cache
                           → validated imports/*.csv + provenance.json
                           → data/catalog.json → index.html + dist/index.html
                           → GitHub Pages
```

Run the collector for the checked scope:

```sh
python3 scripts/ttscore.py --league 777 \
  --ranking 15:2026-08-01 --ranking 10:2026-08-01 \
  --ranking 15:latest --ranking 10:latest
```

Add `--offline` to replay cached responses without network access. Use a **new `--cache` directory** for fresh retrievals. Output replaces the selected scope; repeat all desired league/ranking selections. Use `--output /tmp/ttscore-review` to stage new work. The importer refuses to overwrite manual CSV directories without its manifest.

See [the audit](docs/AUDIT.md) and [TTScore extraction guide](docs/TTSCORE.md) for discovered requests, limitations, reproducibility, and the path to broader historical coverage.

## Validation and provenance

`imports/provenance.json` retains request URL/method/form, retrieval UTC time, response SHA-256, CSV hashes, coverage and review records. Individual source IDs join to that manifest. Raw responses stay in Git-ignored `capture/`; birth years, nationality, contact information and registration notes are not emitted into normalized player records.

The validator rejects duplicate IDs/snapshots, missing references, malformed CSVs, unsafe source URLs, invalid dates, impossible completed game scores, score/winner disagreement, games after a match ends, and changed CSVs with stale provenance. The source importer also reconciles team scores with match sheets. `best_of` defaults to 5; set it explicitly for other match formats. Only `completed` singles count in H2H and win rates; noncompleted CSV records remain visible in histories.

Code changes preserve stable dataset bytes when data are unchanged. CI rebuilds and checks that canonical JSON and portable HTML match the committed versions. To correct source-derived records, update the adapter/source evidence and regenerate the manifest, rather than silently editing generated CSVs.

## Manual/authorized imports

Templates in `imports/*.csv.template` document the supported tables. For separate authorized CSVs use a separate directory and `python3 scripts/import_csv.py --input PATH`. Events, players, clubs, singles matches, official rankings and team fixtures are separate tables. Matches can reference `fixture_id` and historical `club1_id`/`club2_id`. Every match and fixture requires a source URL. No synthetic/test records belong in production CSVs.

Names alone never justify merging athletes. Club IDs based on names remain provisional until official club identity data are available. Maintain correction evidence and review renames explicitly.

## GitHub and free deployment

[Source repository](https://github.com/thanospolimeridis/greek-tt-stats) · [Configured website](https://thanospolimeridis.github.io/greek-tt-stats/)

The repository includes PR validation and a Pages deployment workflow. Pushes to `main` validate the committed source data, build `dist/`, and deploy. No TTScore secrets or service credentials are required by Actions.

GitHub Pages supports public repositories on GitHub Free: [official documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages). Use the default `github.io` address; no purchased domain is required. The application has no hosted backend or recurring service dependency.

## Project structure

| Path | Purpose |
| --- | --- |
| `scripts/ttscore.py` | Public request collector, source parsers and offline replay |
| `scripts/import_csv.py` | Validation and deterministic canonical dataset |
| `scripts/build.py` | Embed CSS, JavaScript and JSON into portable HTML |
| `src/` | Greek/English static application |
| `imports/` | Normalized source CSVs and provenance manifest |
| `data/verified_events.json` | Original prototype's seed listings; not evidence of complete coverage |
| `tests/` | Synthetic parser/validation regressions and frontend behavior checks |
| `docs/` | Audit, observed source schema and remaining work |
| `.github/workflows/` | Validation and free static deployment |

The 2.7 MiB portable page is adequate for this initial dataset. Before broad backfill, split data into static season/player JSON and precompute indexes; retain static hosting. Remaining adapters include individual groups, knockout/consolation, doubles and richer nonplayed statuses. Do not label those gaps complete.

## Licence

Site code is MIT licensed. This grants **no licence to third-party TTScore/federation data**. Public accessibility does not itself settle bulk republication rights. Retain attribution and honor corrections/removal requests. No exact birth dates, birth years, contact details, or unnecessary personal fields are published by this importer.
