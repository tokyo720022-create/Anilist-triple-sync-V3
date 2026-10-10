from unittest.mock import Mock, patch

from triple_sync import cli


def _fake_http():
    fake_http = Mock()
    fake_http.__enter__ = Mock(return_value=fake_http)
    fake_http.__exit__ = Mock(return_value=False)
    return fake_http


def test_auth_check_requires_secret(monkeypatch, capsys):
    monkeypatch.delenv("ANILIST_TARGET_TOKEN", raising=False)
    result = cli.main(["check-anilist-auth"])
    captured = capsys.readouterr()
    assert result == 1
    assert "ANILIST_TARGET_TOKEN" in captured.err


def test_auth_check_verifies_expected_account(monkeypatch, capsys):
    monkeypatch.setenv("ANILIST_TARGET_TOKEN", "fake-secret-token")
    fake_client = Mock()
    fake_client.viewer.return_value = {"id": 123, "name": "Orewatokyo"}
    with (
        patch("triple_sync.cli.HttpClient", return_value=_fake_http()),
        patch("triple_sync.cli.AniListClient", return_value=fake_client),
    ):
        result = cli.main(["check-anilist-auth", "--expected-username", "Orewatokyo"])
    captured = capsys.readouterr()
    assert result == 0
    assert "Orewatokyo (ID 123)" in captured.out
    assert "fake-secret-token" not in captured.out


def test_auth_check_fails_if_token_account_mismatches(monkeypatch, capsys):
    monkeypatch.setenv("ANILIST_TARGET_TOKEN", "fake-secret-token")
    fake_client = Mock()
    fake_client.viewer.return_value = {"id": 123, "name": "AnotherAccount"}
    with (
        patch("triple_sync.cli.HttpClient", return_value=_fake_http()),
        patch("triple_sync.cli.AniListClient", return_value=fake_client),
    ):
        result = cli.main(["check-anilist-auth", "--expected-username", "Orewatokyo"])
    captured = capsys.readouterr()
    assert result == 1
    assert "AnotherAccount" in captured.err
    assert "fake-secret-token" not in captured.out + captured.err
