import pytest
from triple_sync.sync import ChangeKind, compare_progress

def test_first_run_is_silent_baseline():
    change = compare_progress("1", None, {"id": 1, "progress": 30}, first_run=True)
    assert change.kind == ChangeKind.BASELINE
    assert not change.should_notify and not change.should_reward

def test_forward_progress_is_rewardable():
    change = compare_progress("1", {"progress": 4}, {"id": 1, "progress": 6})
    assert change.kind == ChangeKind.PROGRESS and change.delta == 2
    assert change.should_notify and change.should_reward

def test_rollback_does_not_reward():
    change = compare_progress("1", {"progress": 8}, {"id": 1, "progress": 5})
    assert change.kind == ChangeKind.ROLLBACK and change.delta == -3
    assert not change.should_notify and not change.should_reward

def test_metadata_change_does_not_reward():
    change = compare_progress("1", {"progress": 5, "score": 7},
                              {"id": 1, "progress": 5, "score": 9})
    assert change.kind == ChangeKind.METADATA and not change.should_reward

def test_negative_progress_rejected():
    with pytest.raises(ValueError):
        compare_progress("1", None, {"id": 1, "progress": -1})
