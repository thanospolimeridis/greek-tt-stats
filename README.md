# Greek TT Archive — Ελληνική Επιτραπέζια Αντισφαίριση

**A working, zero-runtime-dependency, static website for Greek table tennis results and statistics.**

This is an **independent prototype, not an official HTTF/ΕΦΟΕπΑ service** and not a reimplementation of TTScore's tournament-management product.

## Current state — important

- The website is fully functional and includes **10 authentic Greek competition listings** linked to their actual TTScore event pages (2023–2026). The list is a **verified sample, not the complete event archive**.
- The player, club, individual-match, fixture, H2H and ranking views are implemented and can display CSV-imported data.
- **No individual match results, players, ranking points, or wins have been fabricated.** Those sections show honest empty states until verified structured data are imported.
- There is no verified public TTScore API, bulk CSV export or licensed ingestion arrangement at present. **Do not claim automatic TTScore synchronization or full historical coverage.**
- Container-based development could not access TTScore's site over the network. The optional probe/capture scripts are provided to investigate source access on a network-connected machine. They do not bypass HTTP restrictions or authentication.

## Open the site right now

Double-click `index.html` in a browser. It is a **self-contained HTML file**: all data, styling, and JavaScript are embedded. Internet access is only needed to open the original TTScore links.

The complete site is also in `dist/index.html`.

## Build locally (Python standard library only)

```sh
python3 scripts/import_csv.py
python3 scripts/build.py
python3 -m unittest discover -s tests -v
```

No `npm install`, `pip install`, Node.js, database, Docker, AWS account, commercial API or paid library needed for the **normal site build**.

## Deploy free with GitHub Pages

1. Create a **public** GitHub repository (e.g. `greek-tt-archive`).
2. Upload/commit all source files from this folder and push to the `main` branch.
3. Open GitHub **Settings → Pages → Build and deployment → GitHub Actions**.
4. The included `.github/workflows/deploy.yml` validates the data, builds the website and publishes `dist/index.html` after each push to `main`.
5. The URL is approximately `https://YOUR-USERNAME.github.io/greek-tt-archive/` (GitHub shows the exact link).

**Hosting and build-run cost target: €0**, under GitHub Pages/Actions public-repository terms and usage limits. The default `github.io` URL is free; a custom domain is optional and may cost money. GitHub Pages currently documents a 1 GB published-site limit and a soft 100 GB/month bandwidth limit. This design is suitable for an informational public archive; GitHub Pages is not suitable for a transactional or commercial SaaS application.

## Data architecture

```text
TTScore / Federation source evidence (source URLs and authorized exports)
           |
           v
imports/*.csv + data/verified_events.json  [user-supplied, source-grounded]
           |
           v
scripts/import_csv.py                       [validation + identity checking]
           |
           v
data/catalog.json                          [canonical snapshot]
           |
           v
scripts/build.py                            [embed data + JS + CSS]
           |
           v
dist/index.html                             [single static file]
           |
           v
GitHub Pages                               [public archive; no server]
```

### CSV schema

Create files in the `imports/` folder. Rename copies of `*.csv.template` to `*.csv`, then add UTF-8 data. **Do not populate with test/fabricated athletes.**

| File | Required columns | Useful optional columns |
| --- | --- | --- |
| `events.csv` | `id,name,season,source_url` | `type,region,start_date,end_date` |
| `clubs.csv` | `id,name` | `region` |
| `players.csv` | `id,name` | `club_id,gender,aliases` |
| `matches.csv` | `id,event_id,date,player1_id,player2_id,status` | `winner_id,score1,score2,games,round,source_url,club1_id,club2_id` |
| `rankings.csv` | `id,player_id,category,date,rank,source_url` | `points` |
| `fixtures.csv` | `id,event_id,home_club_id,away_club_id,status` | `date,home_score,away_score,source_url` |

Completed individual matches **must** have `source_url`, `winner_id`, and either set scores or game-by-game scores. A CSV with a missing completed-match source URL is deliberately rejected. One game's score can be written `11:8`, and the complete score as `11:8|9:11|13:11|11:7`; the importer derives `3–1` and cross-checks it against any supplied set score. Winners and player IDs must be consistent. Allowed match statuses: `completed`, `walkover`, `retired`, `cancelled`, `scheduled`. Only `completed` results currently count toward win percentages and head-to-head statistics; walkovers and retirements remain separately represented.

For a ranking snapshot, use the **official published** rank and points, not a rating synthesized by this platform. Ranking snapshots are category-specific and date-specific.

**Important data-model note:** team fixtures and individual matches are separate. The same individual match should have just one ID even if it belongs to a team fixture. Historical player-to-club memberships will eventually require a dedicated import table; the current player record carries their present `club_id` and individual matches can independently carry their contemporaneous `club1_id` and `club2_id`.

### Limitations of this MVP architecture

Embedding all data into one HTML file is ideal for a first release (no backend, very little maintenance) but eventually slows initial page loading once the archive grows into hundreds of thousands of matches. At that scale, **split the dataset into static JSON files by season or player**, or precompute aggregates, while keeping the hosting model free and static. Do not migrate to a paid SQL service just because the dataset grows moderately.

### Data quality and rights

- The primary source of truth for individual results is a verified TTScore/federation record or authorized export.
- Preserve the URL, original event ID, stable athlete IDs, exact score and original publication date where provided.
- Never infer a match result from a schedule or league table.
- Historical coverage is incomplete until explicitly proven otherwise; present statistics as *recorded/imported*, not lifetime totals.
- Bulk republication may require permission even for publicly viewable data. Check TTScore and federation data-reuse terms before a full production import.
- Youth athlete information is personal data: avoid exact birthdays, contact details, unnecessary photos and other sensitive data. Establish a lawful basis and correction/deletion policy prior to publication.

## Investigate TTScore source access

For a **read-only connectivity probe** against **known event URLs**:

```sh
python3 scripts/probe_ttscore.py --max-events 5 --delay 2
```

The script checks robots rules and source availability and writes `probe-report.json`. It does **not** scrape unpublished endpoints, brute-force IDs or bypass access restrictions.

For an optional browser-based examination of the *public* JSON network responses (requires developer-only Playwright):

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
python3 scripts/capture_ttscore.py --event 777
```

This writes `capture/page.html`, a limited JSON network-response capture, and `capture/report.json`. **Keep the capture private**, and inspect it before sharing it: API response JSON might contain personal data. This is diagnostic tooling only, **not a confirmed bulk importer**. Do not run with an authenticated session or attempt to work around access restrictions. If TTScore offers a documented/authorized export, use that instead.

## Maintenance

- With manually supplied verified CSV data: commit updates to GitHub; deployments are automatic.
- With a **future verified permitted API/export feed**: add a scheduled GitHub Actions workflow that fetches the feed, validates it and builds the same static site. The current repository intentionally does **not** pretend that automatic ingestion is already working.
- Monitor source schema changes and duplicate IDs after each update; the import script fails early on inconsistencies.
- No 24/7 application server, database, background worker or purchased hosting is needed.

## File layout

```text
index.html                     Offline-ready website
src/template.html              HTML shell
src/style.css                  Responsive styling
src/app.js                     Browsing, search, results, H2H, rankings
scripts/import_csv.py          CSV validator + canonical dataset builder
scripts/build.py               Self-contained single-file site builder
scripts/probe_ttscore.py       Polite source access diagnostics
scripts/capture_ttscore.py     Optional Playwright public-network capture
data/verified_events.json      Verifiable TTScore event sample
imports/*.template             CSV column templates
tests/                         Data integrity tests
.github/workflows/deploy.yml   Free GitHub Pages deployment
dist/index.html                Publishable build output (generated)
```

## License

Site *code* is MIT licensed (see `LICENSE`). **No license or reuse rights for TTScore, federation, athlete or competition data are granted by the code license.** Source data rights must be determined separately.
