# AniList Triple Sync V3

A clean, modular replacement for the legacy AniList/MAL automation. **GitHub Actions remains the runtime**; there is no always-on bot or web server. `aegis_core.py` is intentionally excluded.

## Current milestone: read-only AniList inventory scan

- Scans one or both media types (`ANIME`, `MANGA`) for the configured AniList username.
- Includes standard and custom-list membership and de-duplicates media entries.
- Calls AniList GraphQL queries only; it never mutates AniList.
- Uses a timeout, bounded retries, and `Retry-After` handling for retryable read operations.
- GitHub Actions runs manually and on a schedule matching the old anime workflow cadence.
- Workflow output contains counts only. It does not upload titles, scores, or progress as artifacts.
- If the profile is private or unavailable, the scan fails clearly rather than silently treating it as an empty list.

## Foundation

- Environment-backed settings and safe config validation
- Atomic JSON persistence that refuses to silently reset corrupt state
- Pure reconciliation primitives for baselines, progress, rollbacks, and metadata changes
- AniList GraphQL and MAL OAuth adapter foundations
- Automated tests and a lint/test GitHub Actions workflow

This is not yet the complete replacement for every legacy feature. MAL list reconciliation, Discord/Telegram/Zulip delivery, achievement and performance tracking, airing alerts, state migrations, and production sync workflows remain future milestones.

## Setup

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\Activate.ps1
python -m pip install -e ".[dev]"
pytest
ruff check .
```

## Configuration

- `ANILIST_USERNAME` — profile to scan (defaults to `Orewatokyo`)
- `ANILIST_TARGET_TOKEN` — optional for public read-only scans; use a GitHub Actions secret if authenticated access is required
- `MAL_CLIENT_ID`, `MAL_CLIENT_SECRET`, `MAL_REFRESH_TOKEN` — required later for full MAL synchronization
- `TRIPLE_SYNC_TIMEOUT` and `TRIPLE_SYNC_RETRIES` — optional HTTP settings

Never put credentials in source files, committed JSON, logs, or example environment files. Revoke/rotate credentials that were exposed in public commits.

## Run a read-only scan locally

```bash
python -m triple_sync.cli scan-anilist --username Orewatokyo --media-type both
```

Use `--media-type anime` or `--media-type manga` to run one type. The generated summary contains scan counts, not the full media list.

## State safety and migration

Do not copy old database files wholesale. Back up the old repository, select the authoritative state, then write and test a versioned migration on copies. Do not enable list mutations until dry-run reconciliation and recovery behavior are tested.

## Roadmap

1. ✅ Modular foundation and read-only inventory scan
2. Dry-run comparison against a versioned persistent baseline
3. MAL inventory reads and explicit AniList↔MAL matching rules
4. Safe, idempotent synchronization writes with per-item failure isolation
5. Optional Discord/Telegram/Zulip integrations
6. Achievement, performance, airing, and Ghost Radar modules
7. Separate anime/manga scheduled workflows with protected state persistence and automated regression tests
