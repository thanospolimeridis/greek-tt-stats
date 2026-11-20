# Project audit — 20 November 2026

This records the initial-release audit. The subsequent [historical backfill](HISTORICAL_IMPORT.md) adds group, knockout, consolation and doubles adapters; current counts are in README and the website’s coverage page.

## Finding

Retain the Python standard-library ingestion pipeline and self-contained static website. No backend, database service, frontend framework, paid API, or npm dependencies are needed for the current archive. GitHub Pages is suitable for this informational project.

The starting project was a usable UI prototype, **not a populated statistics archive**. It had ten seed event listings, zero athletes, zero results, nine passing Python tests and a small JavaScript VM smoke suite. No `.git` directory or remote was present. The original prototype is preserved in the initial Git commit.

## Architecture and completeness

| Area | Initial state | Implemented in this iteration | Remaining limitations |
| --- | --- | --- | --- |
| Source retrieval | Connectivity probes; no working importer | Public UI request discovery, cached Python retrieval, offline replay | Group/knockout/consolation adapters and broad league backfill remain |
| Catalog | Ten manually labelled listings | 518 events reconciled across nine season lists and the All listing | Deleted/unlisted events cannot be established from the public list; one legacy listing retained separately |
| Identity | CSV IDs only | Federation registration number for athletes; event-local fallback; spelling aliases | Club IDs are hashes of exact source names, not federation club IDs; renames need explicit mapping |
| Results | Empty views | 260 singles, 56 team fixtures in A1 men 2025–26 | Four doubles excluded; 128 unused lineup slots excluded; other events not imported |
| Rankings | Empty views | 4,909 rows: men/women on 2026-08-01 and 2026-10-01 | Other dates and age categories not imported; missing rows do not mean unranked |
| Validation | Basic references and score totals | Legal completed games, best-of limits, early termination, fixture links, fixture/match-sheet reconciliation, duplicate snapshot rejection | Source-level errors and identity corrections require review |
| Provenance | URLs and nondeterministic build timestamp | Request method/form, retrieval UTC timestamp, response SHA-256, per-record source ID, CSV hashes, dataset fingerprint | Public responses are not an open-data licence; raw diagnostic captures stay ignored |
| UI | Greek/English routes | Correct score orientation, game details/status, ranking date selector, club results, pagination, coverage disclosure, mobile navigation | Names and categories remain in original source language; H2H selector is still a native list |
| Reproducibility | Wall-clock timestamp changed every import | Byte-stable canonical import/build and offline source replay | Remote sources can change; use a new cache directory for a fresh snapshot |
| CI/deployment | Unconnected workflow | PR validation, deterministic build check, Git version control, Pages deployment | Deployment state and URL are recorded in README |

## Correctness defects addressed

- A profile for player two displayed the score in player-one order; H2H had the same issue.
- Supplying only one aggregate score could evade cross-checking against game scores.
- Impossible completed games such as 11–10 and matches continuing after the winning game were accepted.
- Duplicate seeds could be silently collapsed before validation; malformed CSV row widths and duplicate headers were accepted.
- Completed fixtures did not require a source URL.
- Changing language was not actually asserted by the old frontend test: it inspected a stale HTML string.
- Coverage warnings disappeared when any matches and rankings existed, even with an incomplete archive.
- Mobile CSS hid almost all navigation destinations.
- A malformed percent-encoded route could crash rendering.

## Source investigation

The initial sandbox DNS failure and web-fetch 403 were environment-specific. Direct unauthenticated GET requests succeeded. HEAD briefly redirected to the root, so HEAD was not reliable evidence of GET availability. The application is principally server-rendered PHP fragments loaded through jQuery, not a JSON-only SPA. Several public read-only searches use POST; the old GET-only capture script could not discover these results.

See [TTScore extraction notes](TTSCORE.md) for exact observed requests and the staged route to complete historical extraction. No credentials, unpublished ID enumeration, or access-control workarounds were used.

## Boundaries

This release is a populated, auditable **partial archive**. It does not claim complete historical Greek results. “Validated” means structural and numerical consistency, not independent certification by the federation. Published normalized records omit source birth years, nationality, contact details and registration notes. Code is MIT; third-party data rights remain separate.
