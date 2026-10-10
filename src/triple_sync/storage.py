"""Atomic JSON storage; corrupt state is surfaced, never silently reset."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_MISSING = object()


class StateError(RuntimeError):
    """Persistent state could not safely be read or written."""


def load_json(path: str | Path, *, default: Any = _MISSING) -> Any:
    """Load JSON state with an explicit missing-file default.

    If no default is provided, a missing file returns {}. An explicit
    default=None is preserved so callers can distinguish a first run
    from an existing (but invalid) baseline.
    """
    target = Path(path)
    if not target.exists():
        return {} if default is _MISSING else default
    try:
        with target.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError(f"Unable to safely read state file: {target}") from exc


def save_json_atomic(path: str | Path, data: Any) -> None:
    target = Path(path)
    temporary = target.with_name(target.name + ".tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("w", encoding="utf-8", newline=None) as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False, sort_keys=True)
            stream.write(chr(10))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except (OSError, TypeError, ValueError) as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise StateError(f"Unable to safely write state file: {target}") from exc
