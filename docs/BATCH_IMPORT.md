# Resumable competition imports

`data/import-plan.json` freezes the public inventory and a 2026-11-20 eligibility cutoff. It queues **481 remaining past-dated competitions**, alternating seasons. Eleven competitions had already been processed. Twenty-six are deferred: two have unknown dates and 24 had not finished by the cutoff. The legacy seed listing absent from TTScore's current catalog is not silently added to this queue.

The public catalog covers nine seasons, 2018–19 through 2026–27. Past dates establish eligibility for inspection, not proof that results are complete or that an event actually took place.

## Run or resume

```sh
# Process up to nine event boundaries, with a validated export after each event.
python3 scripts/batch_import.py --limit 9

# Continue the entire remaining queue.
python3 scripts/batch_import.py

# Re-normalize from the local source cache, without network access.
python3 scripts/batch_import.py --offline
```

The default reviewed baseline is `imports/`; the evolving validated bundle is `capture/batch-imports/`. Current status is in `capture/batch-state.json`. A fresh worker handles each event, validates its normalized records, and writes an adapter-versioned checkpoint to `capture/batch-checkpoints/`. The parent merges identities and validates the whole archive before replacing the prior staged export. Failed events are not marked imported; already completed exports survive an interruption.

A checkpoint may be reused only with the same adapter fingerprint. A changed adapter is replayed from cached source responses before its results are reused. Offline runs always re-normalize event source data; they do not rely on normalized checkpoints. Request throttling carries across worker restarts, and the collector remains sequential with at least one second between request starts.

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
- Walkovers, noncountable rubbers, unresolved identities, unknown layouts, missing results, and inconsistent scores remain explicit source issues. The importer never supplies fictional scores to fill them.
- The schedule-wide JSON feed was inspected but contains scheduling information rather than score evidence. Bracket shorthand is not used as a substitute for explicit game-score tables.

`coverage.batch` records attempted and pending counts, pending event IDs, and deferred reasons. Each competition retains phase/category traversal, result counts, and issue counts. “Checked” does not mean a complete historical record. A competition with zero usable results stays visible in the coverage report.

## Validate and publish a staged release

```sh
python3 scripts/import_csv.py --input capture/batch-imports --output /tmp/ttscore-batch-catalog.json
python3 scripts/validate_batch.py --cache capture/ttscore --output capture/release-audit.json
python3 -m unittest discover -s tests -v
node tests/smoke.js
```

The release audit rejects lost or changed baseline records, incomplete queue traversal, misleading event totals, and changed source evidence. Use `--allow-pending` only to inspect an intermediate checkpoint. Preserve the original baseline when promoting a release if you need to repeat the preservation check afterward.

Review preservation of the existing archive and source issues before copying staged CSVs and `provenance.json` into `imports/`. Rebuild with `scripts/import_csv.py` and `scripts/build.py`, then commit and push to the existing GitHub Pages workflow. Neither GitHub Actions nor ordinary site builds contact TTScore.

The website paginates long player histories and coverage tables. Hosted detail views load content-addressed static JSON for the selected event, player, or club; H2H uses the complete selected player's history. Missing downloads show a retry message, never an empty-history claim. Detailed request provenance is downloadable as `provenance.json`; `coverage.json` exposes coverage and exclusions. The complete portable page remains available as `index.html` in local builds and `offline.html` on the hosted site. It retains coverage, source links, and all statistical records without duplicating the full request log.
