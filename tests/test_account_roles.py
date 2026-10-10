from triple_sync.cli import build_parser


def test_auth_defaults_to_target_account(monkeypatch):
    monkeypatch.delenv("ANILIST_TARGET_USERNAME", raising=False)
    args = build_parser().parse_args(["check-anilist-auth"])
    assert args.expected_username == "Orewatokyoo"


def test_scan_defaults_to_source_account(monkeypatch):
    monkeypatch.delenv("ANILIST_SOURCE_USERNAME", raising=False)
    monkeypatch.delenv("ANILIST_USERNAME", raising=False)
    args = build_parser().parse_args(["scan-anilist"])
    assert args.username == "Orewatokyo"
