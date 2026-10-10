import pytest
from triple_sync.config import ConfigurationError, Settings

def test_settings_read_env(monkeypatch):
    monkeypatch.setenv("ANILIST_TARGET_TOKEN", "ani-token")
    monkeypatch.setenv("MAL_CLIENT_ID", "client")
    monkeypatch.setenv("MAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("MAL_REFRESH_TOKEN", "refresh")
    assert Settings.from_env().missing_for_sync() == []

def test_missing_config_lists_names(monkeypatch):
    for key in ("ANILIST_TARGET_TOKEN", "MAL_CLIENT_ID", "MAL_CLIENT_SECRET", "MAL_REFRESH_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    assert len(Settings.from_env().missing_for_sync()) == 4

def test_invalid_timeout_rejected(monkeypatch):
    monkeypatch.setenv("TRIPLE_SYNC_TIMEOUT", "0")
    with pytest.raises(ConfigurationError):
        Settings.from_env()
