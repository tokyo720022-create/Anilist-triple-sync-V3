"""Read-only AniList inventory scanner. It never calls AniList mutations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from triple_sync.integrations.anilist import AniListClient, AniListError

MEDIA_TYPES = {"ANIME", "MANGA"}

INVENTORY_QUERY = """
query ($userName: String!, $type: MediaType!) {
  MediaListCollection(userName: $userName, type: $type) {
    lists {
      name
      isCustomList
      entries {
        id
        status
        score
        progress
        progressVolumes
        repeat
        priority
        private
        updatedAt
        startedAt { year month day }
        completedAt { year month day }
        media {
          id
          idMal
          type
          format
          status
          episodes
          chapters
          volumes
          duration
          title { romaji english native }
          startDate { year month day }
          coverImage { large color }
        }
      }
    }
  }
}
"""


def _date_parts(value: Any) -> dict[str, int | None] | None:
    if not isinstance(value, dict):
        return None
    keys = ("year", "month", "day")
    if all(value.get(key) is None for key in keys):
        return None
    return {key: value.get(key) for key in keys}


def _normalise_entry(entry: dict[str, Any], list_name: str, custom: bool) -> dict[str, Any]:
    media = entry.get("media")
    if not isinstance(media, dict) or media.get("id") is None:
        raise AniListError("AniList returned a list entry without a media ID")
    title = media.get("title") if isinstance(media.get("title"), dict) else {}
    cover = media.get("coverImage") if isinstance(media.get("coverImage"), dict) else {}
    return {
        "media_id": int(media["id"]),
        "mal_id": media.get("idMal"),
        "media_type": media.get("type"),
        "format": media.get("format"),
        "media_status": media.get("status"),
        "title": {
            "romaji": title.get("romaji"),
            "english": title.get("english"),
            "native": title.get("native"),
        },
        "list_status": entry.get("status"),
        "progress": int(entry.get("progress") or 0),
        "progress_volumes": int(entry.get("progressVolumes") or 0),
        "score": float(entry.get("score") or 0),
        "repeat": int(entry.get("repeat") or 0),
        "priority": int(entry.get("priority") or 0),
        "private": bool(entry.get("private", False)),
        "updated_at": int(entry.get("updatedAt") or 0),
        "started_at": _date_parts(entry.get("startedAt")),
        "completed_at": _date_parts(entry.get("completedAt")),
        "episodes": media.get("episodes"),
        "chapters": media.get("chapters"),
        "volumes": media.get("volumes"),
        "duration_minutes": media.get("duration"),
        "start_date": _date_parts(media.get("startDate")),
        "cover_image": {"large": cover.get("large"), "color": cover.get("color")},
        "list_names": [list_name] if list_name else [],
        "custom_list_names": [list_name] if custom and list_name else [],
    }


def scan_inventory(
    client: AniListClient,
    username: str,
    media_type: str,
) -> dict[str, Any]:
    """Read and normalize one user's full AniList collection for one media type."""
    username = username.strip()
    kind = media_type.strip().upper()
    if not username:
        raise ValueError("AniList username must not be empty")
    if kind not in MEDIA_TYPES:
        raise ValueError("media_type must be ANIME or MANGA")

    data = client.execute(
        INVENTORY_QUERY,
        {"userName": username, "type": kind},
    )
    collection = data.get("MediaListCollection")
    if not isinstance(collection, dict) or not isinstance(collection.get("lists"), list):
        raise AniListError(
            f"AniList returned no visible {kind.lower()} list for '{username}'. "
            "The profile may be private, unavailable, or the username may be wrong."
        )

    media_by_id: dict[int, dict[str, Any]] = {}
    for group in collection["lists"]:
        if not isinstance(group, dict):
            continue
        name = str(group.get("name") or "").strip()
        is_custom = bool(group.get("isCustomList", False))
        entries = group.get("entries") or []
        if not isinstance(entries, list):
            raise AniListError(f"AniList returned an invalid list group for '{username}'")
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            record = _normalise_entry(entry, name, is_custom)
            media_id = record["media_id"]
            previous = media_by_id.get(media_id)
            if previous is None:
                media_by_id[media_id] = record
                continue

            # A media entry may be exposed through both status and custom lists.
            previous["list_names"] = sorted(set(previous["list_names"] + record["list_names"]))
            previous["custom_list_names"] = sorted(
                set(previous["custom_list_names"] + record["custom_list_names"])
            )
            if record["updated_at"] > previous["updated_at"]:
                list_names = previous["list_names"]
                custom_names = previous["custom_list_names"]
                media_by_id[media_id] = record
                media_by_id[media_id]["list_names"] = list_names
                media_by_id[media_id]["custom_list_names"] = custom_names

    entries = [media_by_id[key] for key in sorted(media_by_id)]
    return {
        "schema_version": 1,
        "source": "AniList",
        "username": username,
        "media_type": kind,
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entry_count": len(entries),
        "custom_list_memberships": sum(len(item["custom_list_names"]) for item in entries),
        "media": entries,
    }
