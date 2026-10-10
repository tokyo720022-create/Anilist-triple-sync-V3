"""Command-line utilities for the V3 project."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from triple_sync.config import Settings
from triple_sync.http_client import HttpClient
from triple_sync.integrations.anilist import AniListClient, AniListError
from triple_sync.scanner import MEDIA_TYPES, scan_inventory
from triple_sync.storage import StateError, save_json_atomic


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="triple-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check-config", help="Check required configuration for full sync.")
    scan = subparsers.add_parser("scan-anilist", help="Read-only inventory scan; no list changes.")
    scan.add_argument(
        "--username",
        default=os.getenv("ANILIST_USERNAME", "Orewatokyo"),
        help="Public AniList username (default: ANILIST_USERNAME or Orewatokyo).",
    )
    scan.add_argument(
        "--media-type",
        default="both",
        choices=["anime", "manga", "both"],
        help="Collection to inspect (default: both).",
    )
    scan.add_argument(
        "--summary-json",
        default="artifacts/anilist-scan-summary.json",
        help="Where to write a count-only JSON summary (default: %(default)s).",
    )
    return parser


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

    media_types = sorted(MEDIA_TYPES) if args.media_type == "both" else [args.media_type.upper()]
    summaries = []
    try:
        with HttpClient(
            timeout=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
        ) as http:
            client = AniListClient(settings.anilist_token, http=http)
            for media_type in media_types:
                inventory = scan_inventory(client, args.username, media_type)
                summaries.append({
                    "username": inventory["username"],
                    "media_type": inventory["media_type"],
                    "entry_count": inventory["entry_count"],
                    "custom_list_memberships": inventory["custom_list_memberships"],
                    "scanned_at": inventory["scanned_at"],
                })
                print(
                    f"Read-only {media_type.lower()} scan: "
                    f"{inventory['entry_count']} unique entries; "
                    f"{inventory['custom_list_memberships']} custom-list memberships."
                )
    except (AniListError, OSError, ValueError) as exc:
        print(f"Scan failed: {exc}", file=sys.stderr)
        return 1

    # The workflow publishes only counts, never titles, scores, or progress.
    report = {
        "schema_version": 1,
        "mode": "read-only",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scans": summaries,
    }
    try:
        save_json_atomic(Path(args.summary_json), report)
    except (OSError, StateError) as exc:
        print(f"Could not write scan summary: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2))
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as stream:
            stream.write("## AniList V3 read-only scan\n\n")
            stream.write("| Profile | Type | Entries | Custom-list memberships |\n")
            stream.write("|---|---:|---:|---:|\n")
            for item in summaries:
                stream.write(
                    f"| {item['username']} | {item['media_type']} | "
                    f"{item['entry_count']} | {item['custom_list_memberships']} |\\n"
                )
            stream.write("\nNo AniList list was modified. Full titles, scores, and progress were not saved to the workflow artifact.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
