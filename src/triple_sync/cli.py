"""Command-line utilities for the V3 project."""
from __future__ import annotations

import argparse
import json
import os
import sys

import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from triple_sync.config import Settings
from triple_sync.dry_run import build_snapshot, compare_snapshots, profile_key
from triple_sync.http_client import HttpClient
from triple_sync.integrations.anilist import AniListClient, AniListError
from triple_sync.scanner import MEDIA_TYPES, scan_inventory
from triple_sync.storage import StateError, load_json, save_json_atomic


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="triple-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check-config", help="Check required configuration for full sync.")
    auth = subparsers.add_parser(
        "check-anilist-auth",
        help="Verify the AniList access token using the authenticated Viewer query.",
    )
    auth.add_argument(
        "--expected-username",
        default=os.getenv("ANILIST_TARGET_USERNAME", "Orewatokyoo"),
        help="Expected target AniList account (default: ANILIST_TARGET_USERNAME or Orewatokyoo).",
    )
    scan = subparsers.add_parser(
        "scan-anilist", help="Read-only inventory scan and dry-run comparison; no list changes."
    )
    scan.add_argument(
        "--username", default=os.getenv("ANILIST_SOURCE_USERNAME", os.getenv("ANILIST_USERNAME", "Orewatokyo")),
        help="Source AniList username (default: ANILIST_SOURCE_USERNAME or Orewatokyo).",
    )
    scan.add_argument(
        "--media-type", default="both", choices=["anime", "manga", "both"],
        help="Collection to inspect (default: both).",
    )
    scan.add_argument(
        "--state-dir", default="sync-state",
        help="Directory containing previous minimal state snapshots.",
    )
    scan.add_argument(
        "--summary-json", default="artifacts/anilist-dry-run-summary.json",
        help="Where to write an aggregate-only JSON report.",
    )
    return parser


def _load_previous_baseline(state_path: Path) -> dict[str, Any] | None:
    """Return None only when the baseline file truly does not exist."""
    if not state_path.exists():
        return None
    previous = load_json(state_path)
    if not isinstance(previous, dict):
        raise StateError(
            f"Invalid baseline in {state_path}; refusing to overwrite it"
        )
    return previous


def _summary_markdown(summaries: list[dict[str, Any]]) -> str:
    lines = [
        "## AniList V3 read-only dry-run", "",
        "| Profile | Type | Mode | Tracked | Advanced | Rollbacks | New | Removed |", 
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in summaries:
        diff = item["comparison"]
        lines.append(
            f"| {item['username']} | {item['media_type']} | {diff['mode']} | "
            f"{diff['tracked_entries']} | {diff['progress_advanced_entries']} | "
            f"{diff['progress_rollback_entries']} | {diff['new_entries']} | {diff['removed_entries']} |"
        )
    lines.extend([
        "", "No AniList list was modified and no notifications were sent.",
        "State snapshots exclude entries marked private, titles, and cover URLs. This is a public repository, so treat artifacts as public; set the repository private if you do not want progress/score history exposed.",
    ])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.from_env()

    if args.command == "check-config":
        missing = settings.missing_for_sync()
        if missing:
            print("Missing required environment variables:")
            print("\n".join(f"  - {name}" for name in missing))
            return 1
        print("Required AniList and MAL configuration is present.")
        return 0

    if args.command == "check-anilist-auth":
        # A public profile scan can succeed without a token; this command cannot.
        if not settings.anilist_token:
            print("Missing ANILIST_TARGET_TOKEN; add it as a GitHub Actions secret.", file=sys.stderr)
            return 1
        expected = args.expected_username.strip()
        if not expected:
            print("Expected AniList username must not be empty.", file=sys.stderr)
            return 1
        try:
            with HttpClient(
                timeout=settings.request_timeout_seconds,
                max_retries=settings.max_retries,
            ) as http:
                viewer = AniListClient(settings.anilist_token, http=http).viewer()
        except (AniListError, requests.RequestException, OSError, ValueError) as exc:
            print(f"AniList authentication check failed: {exc}", file=sys.stderr)
            return 1

        actual = str(viewer.get("name") or "").strip()
        viewer_id = viewer.get("id")
        if not actual or viewer_id is None:
            print("AniList Viewer response did not include an account name and ID.", file=sys.stderr)
            return 1
        if actual.casefold() != expected.casefold():
            print(
                f"AniList token belongs to '{actual}' (ID {viewer_id}), "
                f"but expected '{expected}'. No list was modified.",
                file=sys.stderr,
            )
            return 1
        print(f"AniList authentication verified: {actual} (ID {viewer_id}).")
        print("Token value was not displayed; no AniList list was modified.")
        return 0

    media_types = sorted(MEDIA_TYPES) if args.media_type == "both" else [args.media_type.upper()]
    state_dir = Path(args.state_dir)
    summaries: list[dict[str, Any]] = []
    staged_snapshots: dict[Path, dict[str, Any]] = {}
    try:
        with HttpClient(
            timeout=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
        ) as http:
            client = AniListClient(settings.anilist_token, http=http)
            for media_type in media_types:
                inventory = scan_inventory(client, args.username, media_type)
                current_snapshot = build_snapshot(inventory)
                state_path = state_dir / f"{profile_key(args.username)}-{media_type.lower()}.json"
                previous = _load_previous_baseline(state_path)
                comparison = compare_snapshots(previous, current_snapshot)
                staged_snapshots[state_path] = current_snapshot
                summary = {
                    "username": inventory["username"],
                    "media_type": inventory["media_type"],
                    "scanned_at": inventory["scanned_at"],
                    "custom_list_memberships": inventory["custom_list_memberships"],
                    "private_entries_excluded": current_snapshot["private_entries_excluded"],
                    "comparison": comparison,
                }
                summaries.append(summary)
                print(
                    f"Read-only {media_type.lower()} {comparison['mode']}: "
                    f"{comparison['tracked_entries']} tracked; "
                    f"{comparison['progress_advanced_entries']} progress increases; "
                    f"{comparison['progress_rollback_entries']} rollbacks; "
                    f"{comparison['new_entries']} new; {comparison['removed_entries']} removed."
                )

        # Only persist state after every requested media type scanned and compared successfully.
        for path, snapshot in staged_snapshots.items():
            save_json_atomic(path, snapshot)
    except (AniListError, OSError, ValueError, StateError) as exc:
        print(f"Scan/dry-run failed: {exc}", file=sys.stderr)
        return 1

    report = {
        "schema_version": 1,
        "mode": "read-only-dry-run",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scans": summaries,
    }
    try:
        save_json_atomic(Path(args.summary_json), report)
    except (OSError, StateError) as exc:
        print(f"Could not write dry-run summary: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2))
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as stream:
                stream.write(_summary_markdown(summaries))
        except OSError as exc:
            print(f"Could not write GitHub step summary: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
