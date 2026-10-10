# AniList Triple Sync V3

A clean, modular replacement for the legacy AniList/MAL automation. **GitHub Actions remains the runtime**; there is no always-on bot or web server. `aegis_core.py` is intentionally excluded.

## Current milestone: read-only AniList inventory and dry-run comparison

- Scans anime and manga collections for the configured AniList username.
- Includes standard and custom-list memberships and de-duplicates entries by media ID.
- Compares each scan with a prior minimal baseline and reports aggregate changes only.
- Calls AniList GraphQL queries only; it never mutates AniList or sends notifications.
- The GitHub Actions workflow runs manually and on a three-hour schedule matching the old anime workflow cadence.
- If no baseline artifact is available, the run establishes a silent baseline instead of inventing activity.
- State snapshots omit entries marked private, titles, and cover URLs. They still contain IDs, progress, scores, statuses, repeat counts, custom-list names, and timestamps needed for comparisons.

**Public-repository privacy warning:** workflow artifacts can be downloaded by people with read access to the repository. Because this repo is public, treat the baseline and report artifacts as public. Make the repository private before using this workflow if you do not want progress/score history exposed. The baseline is stored as an Actions artifact, not committed into Git history, and has 90-day retention.

## Included foundation

- Environment-backed settings and configuration validation
- HTTP timeouts, bounded retries, and `Retry-After` support for retryable reads
- Atomic JSON persistence that refuses to silently reset corrupt state
- AniList GraphQL client and MAL OAuth refresh adapter foundation
- Pure reconciliation primitives for baseline, progress, rollback, and metadata changes
- Aggregate-only dry-run reporting
- Automated tests, linting, and a GitHub Actions test workflow

This is not yet the complete replacement for every legacy feature. MAL list reconciliation, Discord/Telegram/Zulip delivery, achievement and performance tracking, airing alerts, Ghost Radar, state migration, and real sync writes remain future milestones.

## Setup

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
ruff check .
```

## Configuration

- `ANILIST_USERNAME` — profile to scan (defaults to `Orewatokyo`)
- `ANILIST_TARGET_TOKEN` — optional for public read-only scans; use a GitHub Actions secret when authenticated access is required
- `MAL_CLIENT_ID`, `MAL_CLIENT_SECRET`, `MAL_REFRESH_TOKEN` — required later for full MAL synchronization
- `TRIPLE_SYNC_TIMEOUT` and `TRIPLE_SYNC_RETRIES` — optional HTTP settings

Never put credentials in source files, committed JSON, logs, or example environment files. Revoke/rotate credentials that were exposed in public commits.

## Run a read-only dry-run locally

```bash
python -m triple_sync.cli scan-anilist --username Orewatokyo --media-type both
```

Use `--media-type anime` or `--media-type manga` for one collection. Local snapshots default to `.sync-state/`; the aggregate-only report defaults to `artifacts/anilist-dry-run-summary.json`.

## State safety and migration

Do not copy old database files wholesale. Back up the old repository, select authoritative state, then write and test a versioned migration on copies. Current V3 does not update AniList or MAL and does not send notifications.

## Roadmap

1. ✅ Modular foundation and read-only inventory scan
2. ✅ Aggregate-only dry-run comparison against an artifact-persisted baseline
3. MAL inventory reads and explicit AniList↔MAL matching rules
4. Safe, idempotent synchronization writes with per-item failure isolation
5. Optional Discord/Telegram/Zulip adapters
6. Achievement, performance, airing, and Ghost Radar modules
7. Separate anime/manga scheduled workflows with protected state persistence and automated regression tests
