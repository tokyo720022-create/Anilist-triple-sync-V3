import pytest

from triple_sync.dry_run import build_snapshot, compare_snapshots, profile_key


def _inventory(items):
    return {"username": "Orewatokyo", "media_type": "ANIME", "scanned_at": "now", "media": items}


def _item(media_id, progress=0, status="CURRENT", score=0, repeat=0, custom=None, private=False):
    return {
        "media_id": media_id, "progress": progress, "list_status": status, "score": score,
        "repeat": repeat, "custom_list_names": custom or [], "updated_at": 42,
        "private": private, "title": {"romaji": "Sensitive title"},
        "cover_image": {"large": "https://example.test/cover.jpg"},
    }


def test_snapshot_keeps_minimum_fields_and_excludes_private_entries():
    snapshot = build_snapshot(_inventory([_item(1, progress=2, custom=["Favourite"]), _item(2, private=True)]))
    assert snapshot["entry_count"] == 1
    assert snapshot["private_entries_excluded"] == 1
    assert set(snapshot["entries"]["1"]) == {"progress", "status", "score", "repeat", "custom_list_names", "updated_at"}
    assert "Sensitive title" not in str(snapshot)
    assert "cover.jpg" not in str(snapshot)


def test_first_run_establishes_baseline_without_fake_activity():
    current = build_snapshot(_inventory([_item(1, progress=12), _item(2, progress=4)]))
    report = compare_snapshots(None, current)
    assert report["mode"] == "baseline"
    assert report["tracked_entries"] == 2
    assert report["progress_advanced_entries"] == 0
    assert report["new_entries"] == 0


def test_reports_progress_metadata_custom_membership_and_removal():
    old = build_snapshot(_inventory([
        _item(1, progress=2, status="CURRENT", score=5, custom=["Favourite"]),
        _item(2, progress=9),
        _item(3, progress=1),
    ]))
    new = build_snapshot(_inventory([
        _item(1, progress=5, status="COMPLETED", score=8, custom=["Planning"]),
        _item(2, progress=4),
        _item(4, progress=2),
    ]))
    report = compare_snapshots(old, new)
    assert report["mode"] == "dry-run"
    assert report["progress_advanced_entries"] == 1
    assert report["progress_units_advanced"] == 3
    assert report["progress_rollback_entries"] == 1
    assert report["status_changes"] == 1
    assert report["score_changes"] == 1
    assert report["custom_list_changes"] == 1
    assert report["new_entries"] == 1
    assert report["removed_entries"] == 1
    assert "Sensitive title" not in str(report)


def test_mismatched_baseline_is_not_silently_accepted():
    previous = build_snapshot(_inventory([_item(1)]))
    current = build_snapshot({**_inventory([_item(1)]), "username": "other-user"})
    with pytest.raises(ValueError, match="username"):
        compare_snapshots(previous, current)


def test_profile_key_is_safe_and_deterministic():
    assert profile_key("Orewatokyo") == "orewatokyo"
    assert profile_key("a/../../bad username") == "a_bad_username"
    with pytest.raises(ValueError):
        profile_key("///")


def test_missing_baseline_load_semantics(tmp_path):
    from triple_sync.storage import load_json

    previous = load_json(tmp_path / "no-baseline.json", default=None)
    assert previous is None
    current = build_snapshot(_inventory([_item(99, progress=10)]))
    report = compare_snapshots(previous, current)
    assert report["mode"] == "baseline"
    assert report["progress_advanced_entries"] == 0


def test_existing_null_baseline_is_rejected(tmp_path):
    from triple_sync.cli import _load_previous_baseline
    from triple_sync.storage import StateError

    path = tmp_path / "baseline.json"
    path.write_text("null", encoding="utf-8")
    with pytest.raises(StateError, match="refusing to overwrite"):
        _load_previous_baseline(path)
