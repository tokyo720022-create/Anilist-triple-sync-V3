from unittest.mock import Mock
import pytest
from triple_sync.integrations.anilist import AniListClient, AniListError

def test_viewer_query_returns_viewer():
    http = Mock()
    response = Mock(ok=True)
    response.json.return_value = {"data": {"Viewer": {"id": 42, "name": "Tokyo"}}}
    http.request.return_value = response
    assert AniListClient("token", http=http).viewer() == {"id": 42, "name": "Tokyo"}

def test_graphql_errors_raise():
    http = Mock()
    response = Mock(ok=True)
    response.json.return_value = {"errors": [{"message": "Not authorized"}]}
    http.request.return_value = response
    with pytest.raises(AniListError, match="Not authorized"):
        AniListClient("token", http=http).execute("query { Viewer { id } }")

def test_empty_token_rejected():
    with pytest.raises(ValueError):
        AniListClient(" ")
