import json
import pytest
from triple_sync.storage import StateError, load_json, save_json_atomic

def test_missing_file_uses_default(tmp_path):
    assert load_json(tmp_path / "missing.json") == {}

def test_atomic_round_trip(tmp_path):
    path = tmp_path / "state" / "sync.json"
    save_json_atomic(path, {"episode": 7, "title": "Tokyo"})
    assert json.loads(path.read_text(encoding="utf-8"))["episode"] == 7
    assert not path.with_name("sync.json.tmp").exists()

def test_corrupt_state_is_not_silently_reset(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(StateError):
        load_json(path)


def test_missing_file_explicit_none_is_preserved(tmp_path):
    # Dry-run startup uses None to mean "no baseline yet".
    assert load_json(tmp_path / "not-created.json", default=None) is None


def test_missing_file_explicit_none_is_preserved(tmp_path):
    assert load_json(tmp_path / "no-baseline.json", default=None) is None
