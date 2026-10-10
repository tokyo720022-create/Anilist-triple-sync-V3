# AniList Triple Sync V3

Clean, modular foundation for AniList and MyAnimeList synchronization. `aegis_core.py` is intentionally excluded.

## Included
- Environment-backed configuration (never logs secret values)
- HTTP timeouts, bounded retry handling, `Retry-After` support
- Atomic JSON persistence that refuses to silently reset corrupt state
- AniList GraphQL client and MAL OAuth refresh adapter
- Pure reconciliation primitives for baseline, progress, rollback, and metadata changes
- CLI configuration check, automated tests, lint/test workflow

This is a foundation, not a full migration of every old feature. Full inventory sync, notifications, and scheduled production workflows should be added after these primitives pass review.

## Setup
Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\Activate.ps1
python -m pip install -e ".[dev]"
triple-sync check-config
pytest
ruff check .
```

Copy `.env.example` to `.env` for local development and load it using your preferred environment manager. Never commit credentials. Revoke/rotate any credential that was exposed in a public commit.

## Required environment variables
- `ANILIST_TARGET_TOKEN`
- `MAL_CLIENT_ID`
- `MAL_CLIENT_SECRET`
- `MAL_REFRESH_TOKEN`

Do not copy legacy JSON databases wholesale. Back up old state and create a tested, versioned migration before importing selected data.
