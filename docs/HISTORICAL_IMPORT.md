# Historical backfill adapters

The checked-in `data/backfill-plan.json` selects tournaments spanning all nine publicly listed seasons, including national doubles and mixed doubles. This is an expansion across seasons, **not a claim that every competition has been imported**. Existing league singles and ranking snapshots are retained.

```sh
python3 scripts/historical.py --balanced --event 839 --output /tmp/tt-history-review
python3 scripts/import_csv.py --input /tmp/tt-history-review --output /tmp/tt-history-review/catalog.json
# Same commands with --offline reproduce source normalization from the local cache.
```

Use repeatable `--event ID` for other catalogued tournaments. `--all-events` requests traversal of the catalog; unsupported team-tournament formats, source anomalies, future/ongoing events, and missing identities must be reviewed. `--category-limit N` is a development option that explicitly records selected/discovered category counts; do not describe limited runs as whole-event coverage.

## Validated release — 20 November 2026

The expanded archive contains **1,865 singles and 117 doubles** across 11 competitions and all nine listed seasons. All 260 previous singles, 56 fixtures, 4,909 ranking rows and existing athlete identities were preserved. The four previously excluded league doubles are now imported.

| Season | Tournament | Singles | Doubles | Flagged records |
| --- | --- | ---: | ---: | ---: |
| 2018-19 | [287](https://app.ttscore.io/customer/24/event/287) | 50 | 0 | 0 |
| 2019-20 | [364](https://app.ttscore.io/customer/24/event/364) | 91 | 23 | 0 |
| 2020-21 | [416](https://app.ttscore.io/customer/24/event/416) | 141 | 26 | 3 |
| 2021-22 | [510](https://app.ttscore.io/customer/24/event/510) | 11 | 0 | 0 |
| 2022-23 | [585](https://app.ttscore.io/customer/24/event/585) | 84 | 0 | 1 |
| 2023-24 | [681](https://app.ttscore.io/customer/24/event/681) | 241 | 0 | 6 |
| 2024-25 | [753](https://app.ttscore.io/customer/24/event/753) | 215 | 0 | 5 |
| 2025-26 | [839](https://app.ttscore.io/customer/24/event/839) | 136 | 64 | 20 |
| 2025-26 | [857](https://app.ttscore.io/customer/24/event/857) | 225 | 0 | 6 |
| 2026-27 | [898](https://app.ttscore.io/customer/24/event/898) | 411 | 0 | 1 |

The remaining 260 singles and four doubles belong to league 777. Tournament exclusions are 41 explicit walkovers and one source record with an impossible 0–0 game inside a declared completed match. Seven unplayed/bye slots and 128 unused league lineup slots are also omitted. These are recorded separately from played results.

The six initially ambiguous group matches in event 857 were resolved using the participant IDs in each individual group table: two athletes share the same abbreviated display name in different groups. A regression test prevents page-wide name matching from merging or obscuring them.

Validation: 56 Python tests, 37 frontend checks, source/score/reference checks, preservation checks against the prior archive, and byte-identical CSV/manifest output from two offline imports. Raw capture hashes, adapter hashes, coverage and source issues are retained in the manifest. Only the normalized CSVs and request metadata are published.

This is selected tournament coverage, **not 518 completely imported competitions**. Public traversal cannot establish whether TTScore has deleted or unlisted older records.

## Extraction and validation

- **Groups:** discover categories, fetch group tables, follow every source `nextPage` link, and fetch explicit game-score tables. Resolve abbreviated labels only within the group’s identified participants and only when the mapping is unique. Federation registration numbers from the participant response establish identity; names never merge athletes across events.
- **Knockout:** traverse every bracket and placement round. Bind game IDs to participant IDs from adjacent bracket entries. Fetch full point scores using the group IDs present in the bracket; never decode ambiguous shorthand score spans.
- **Consolation:** the same bracket adapter, using the source’s separately linked series selector. Canonical game IDs prevent double counting across views; conflicting duplicates are rejected.
- **Tournament doubles/mixed doubles:** preserve the source game ID, exact displayed pair labels, category, scores and provenance. Where the public view lacks member IDs, `identity_status=source_pair_labels_only` explicitly prevents links to individual profiles. Do not turn abbreviated names into invented athlete IDs or merge similarly named pairs.
- **Team doubles:** all four members are linked by the registration numbers in the match sheet; they appear in the relevant individual histories in a separate doubles section. Singles win rates and H2H exclude doubles.

Completed scores must agree with legal point scores and stop when the match is won. Byes and empty scores are not wins. Walkovers, incomplete scores, unresolved mappings and unsupported team-tournament schedules are retained as coverage issues, not invented results. `imports/provenance.json` records phase, game, source hash and reason.

Each selected event has discovered/selected phase-category counts (one category can occur in several phases), visited group count, normalized singles/doubles counts, unplayed slots and issue count. `public_views_traversed` means the selected public views were visited; `historical_complete` remains false. It does not certify source completeness or deleted records.

## Reproducibility and privacy

Raw responses and per-event checkpoints stay in ignored `capture/`. Participant responses can contain contact and birth information; the normalizer emits only explicitly allowlisted competition identity fields. Do not publish raw captures. Checkpoints are tied to adapter code hashes; reprocessing revised adapters uses cached raw responses instead of stale normalized rows. `--offline` always re-normalizes raw responses, bypassing normalized checkpoints. A missing, corrupt or unreadable cache aborts the run. The manifest records the adapter and backfill-plan hashes.

The staged CSV bundle and provenance are validated before promotion. Source requests are cached and limited to one per second. No authentication, write endpoints, or ID enumeration is used. Ordinary site builds and GitHub Actions remain offline and reproducible from the committed CSVs. Exact source replay additionally requires the local raw cache; a later fresh retrieval can differ if TTScore changes its records.
