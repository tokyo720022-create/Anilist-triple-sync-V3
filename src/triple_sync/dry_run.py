"""Private minimal state snapshots and read-only change summaries."""
from __future__ import annotations

from typing import Any
import re

from triple_sync.sync import compare_progress

STATE_SCHEMA_VERSION = 1


def build_snapshot(inventory: dict[str, Any]) -> dict[str, Any]:
    """Retain only fields needed to compare future runs; omit titles and cover URLs.

    Entries marked private are intentionally excluded because the repository is public.
    The workflow stores this compact state as a GitHub Actions artifact rather than a commit.
    """
    entries: dict[str, dict[str, Any]] = {}
    private_excluded = 0
    for media in inventory.get("media", []):
        if media.get("private", False):
            private_excluded += 1
            continue
        raw_id = media.get("media_id")
        if raw_id is None:
            raise ValueError("Inventory item is missing media_id")
        key = str(int(raw_id))
        entries[key] = {
            "progress": int(media.get("progress") or 0),
            "status": str(media.get("list_status") or ""),
            "score": float(media.get("score") or 0),
            "repeat": int(media.get("repeat") or 0),
            "custom_list_names": sorted({str(n) for n in (media.get("custom_list_names") or [])}),
            "updated_at": int(media.get("updated_at") or 0),
        }
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "username": str(inventory["username"]),
        "media_type": str(inventory["media_type"]).upper(),
        "scanned_at": str(inventory.get("scanned_at") or ""),
        "entry_count": len(entries),
        "entries": entries,
        "private_entries_excluded": private_excluded,
    }


def compare_snapshots(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    """Return aggregate counts only; never include media titles or entry-level values."""
    current_entries = current.get("entries")
    if not isinstance(current_entries, dict):
        raise ValueError("Current snapshot does not contain a valid entries mapping")

    counts = {
        "tracked_entries": len(current_entries),
        "new_entries": 0,
        "removed_entries": 0,
        "progress_advanced_entries": 0,
        "progress_units_advanced": 0,
        "progress_rollback_entries": 0,
        "status_changes": 0,
        "score_changes": 0,
        "repeat_changes": 0,
        "custom_list_changes": 0,
        "unchanged_entries": 0,
        "changed_existing_entries": 0,
    }

    if previous is None:
        return {
            "mode": "baseline",
            "message": "No prior baseline was found; current state was recorded without activity events.",
            **counts,
        }

    if previous.get("schema_version") != STATE_SCHEMA_VERSION:
        raise ValueError("Baseline schema version is unsupported; refusing to reset it")
    if previous.get("username") != current.get("username"):
        raise ValueError("Baseline username does not match the requested profile")
    if previous.get("media_type") != current.get("media_type"):
        raise ValueError("Baseline media type does not match the current scan")
    old_entries = previous.get("entries")
    if not isinstance(old_entries, dict):
        raise ValueError("Baseline does not contain a valid entries mapping; refusing to reset it")

    old_ids = set(old_entries)
    new_ids = set(current_entries)
    counts["new_entries"] = len(new_ids - old_ids)
    counts["removed_entries"] = len(old_ids - new_ids)

    for media_id in sorted(old_ids & new_ids):
        old = old_entries[media_id]
        new = current_entries[media_id]
        change = compare_progress(media_id, old, new)
        changed = False
        if change.delta > 0:
            counts["progress_advanced_entries"] += 1
            counts["progress_units_advanced"] += change.delta
            changed = True
        elif change.delta < 0:
            counts["progress_rollback_entries"] += 1
            changed = True
        if old.get("status") != new.get("status"):
            counts["status_changes"] += 1
            changed = True
        if old.get("score") != new.get("score"):
            counts["score_changes"] += 1
            changed = True
        if old.get("repeat") != new.get("repeat"):
            counts["repeat_changes"] += 1
            changed = True
        if old.get("custom_list_names", []) != new.get("custom_list_names", []):
            counts["custom_list_changes"] += 1
            changed = True
        if changed:
            counts["changed_existing_entries"] += 1
        else:
            counts["unchanged_entries"] += 1

    return {
        "mode": "dry-run",
        "message": "Compared with the previous baseline; no external list was modified and no notifications were sent.",
        **counts,
    }


def profile_key(username: str) -> str:
    """Return a safe, deterministic filename prefix for a profile username."""
    key = re.sub(r"[^A-Za-z0-9_-]+", "_", username.strip()).strip("_").lower()
    if not key:
        raise ValueError("Username cannot be converted to a safe state filename")
    return key
