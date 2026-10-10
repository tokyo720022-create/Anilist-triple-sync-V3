from unittest.mock import Mock

import pytest

from triple_sync.integrations.anilist import AniListClient, AniListError


def test_viewer_query_returns_viewer():
    http = Mock()
    response = Mock(ok=True)
    response.json.return_value = {"data": {"Viewer": {"id": 42, "name": "Tokyo"}}}
    http.request.return_value = response
    assert AniListClient("token", http=http).viewer() == {"id": 42, "name": "Tokyo"}
    kwargs = http.request.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer token"
    assert kwargs["retryable"] is True


def test_public_read_can_run_without_token():
    http = Mock()
    response = Mock(ok=True)
    response.json.return_value = {"data": {"Viewer": {"id": 42, "name": "Tokyo"}}}
    http.request.return_value = response
    assert AniListClient("", http=http).viewer()["name"] == "Tokyo"
    assert "Authorization" not in http.request.call_args.kwargs["headers"]


def test_graphql_errors_raise():
    http = Mock()
    response = Mock(ok=True)
    response.json.return_value = {"errors": [{"message": "Not authorized"}]}
    http.request.return_value = response
    with pytest.raises(AniListError, match="Not authorized"):
        AniListClient("token", http=http).execute("query { Viewer { id } }")


def test_mutation_is_not_marked_retryable():
    http = Mock()
    response = Mock(ok=True)
    response.json.return_value = {"data": {"SaveMediaListEntry": {"id": 1}}}
    http.request.return_value = response
    AniListClient("token", http=http).execute("mutation { SaveMediaListEntry(id: 1) { id } }")
    assert http.request.call_args.kwargs["retryable"] is False
