import pytest

from triple_sync.integrations.anilist import AniListError
from triple_sync.scanner import INVENTORY_QUERY, scan_inventory


class FakeAniList:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def execute(self, query, variables=None):
        self.calls.append((query, variables))
        return self.data


def _entry(media_id, *, updated=100, progress=3, title="Sample", score=8):
    return {
        "id": media_id + 1000,
        "status": "CURRENT",
        "score": score,
        "progress": progress,
        "progressVolumes": 0,
        "repeat": 0,
        "priority": 0,
        "private": False,
        "updatedAt": updated,
        "startedAt": {"year": 2024, "month": 1, "day": 2},
        "completedAt": {"year": None, "month": None, "day": None},
        "media": {
            "id": media_id, "idMal": media_id + 10, "type": "ANIME",
            "format": "TV", "status": "FINISHED", "episodes": 12,
            "chapters": None, "volumes": None, "duration": 24,
            "title": {"romaji": title, "english": None, "native": None},
            "startDate": {"year": 2020, "month": 1, "day": 1},
            "coverImage": {"large": "https://example.test/cover.jpg", "color": "#123456"},
        },
    }


def test_scans_and_merges_custom_list_membership():
    original = _entry(1, updated=100, title="One")
    custom_copy = _entry(1, updated=100, title="One")
    other = _entry(2, updated=200, title="Two", progress=7)
    client = FakeAniList({"MediaListCollection": {"lists": [
        {"name": "Watching", "isCustomList": False, "entries": [original, other]},
        {"name": "Favourite", "isCustomList": True, "entries": [custom_copy]},
    ]}})
    result = scan_inventory(client, " Orewatokyo ", "anime")
    assert result["entry_count"] == 2
    assert result["media_type"] == "ANIME"
    assert result["media"][0]["list_names"] == ["Favourite", "Watching"]
    assert result["media"][0]["custom_list_names"] == ["Favourite"]
    assert client.calls[0][1] == {"userName": "Orewatokyo", "type": "ANIME"}
    assert "mutation" not in INVENTORY_QUERY.lower()


def test_private_or_missing_list_returns_clear_error():
    client = FakeAniList({"MediaListCollection": None})
    with pytest.raises(AniListError, match="no visible anime list"):
        scan_inventory(client, "private-user", "ANIME")


@pytest.mark.parametrize("media_type", ["other", "", "MAL"])
def test_rejects_unsupported_type(media_type):
    with pytest.raises(ValueError, match="media_type"):
        scan_inventory(FakeAniList({}), "Orewatokyo", media_type)


def test_rejects_empty_username():
    with pytest.raises(ValueError, match="username"):
        scan_inventory(FakeAniList({}), "  ", "MANGA")
