"""Pure reconciliation primitives; no network or storage side effects."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

class ChangeKind(StrEnum):
    BASELINE = "baseline"
    NEW_ENTRY = "new_entry"
    PROGRESS = "progress"
    ROLLBACK = "rollback"
    METADATA = "metadata"
    UNCHANGED = "unchanged"

@dataclass(frozen=True, slots=True)
class Change:
    media_id: str
    kind: ChangeKind
    old_progress: int | None
    new_progress: int
    delta: int
    should_notify: bool
    should_reward: bool

def compare_progress(media_id: str, old: dict[str, Any] | None, new: dict[str, Any],
                     *, first_run: bool = False) -> Change:
    key = str(new.get("id", media_id))
    try:
        current = int(new.get("progress") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid progress for media {key}") from exc
    if current < 0:
        raise ValueError(f"Progress cannot be negative for media {key}")
    if old is None:
        kind = ChangeKind.BASELINE if first_run else ChangeKind.NEW_ENTRY
        return Change(key, kind, None, current, 0, False, False)
    try:
        previous = int(old.get("progress") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid stored progress for media {key}") from exc
    delta = current - previous
    if delta > 0:
        return Change(key, ChangeKind.PROGRESS, previous, current, delta, True, True)
    if delta < 0:
        return Change(key, ChangeKind.ROLLBACK, previous, current, delta, False, False)
    if old.get("score") != new.get("score") or old.get("status") != new.get("status"):
        return Change(key, ChangeKind.METADATA, previous, current, 0, True, False)
    return Change(key, ChangeKind.UNCHANGED, previous, current, 0, False, False)
