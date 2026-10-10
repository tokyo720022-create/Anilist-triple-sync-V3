"""Minimal AniList GraphQL client."""
from typing import Any
from triple_sync.http_client import HttpClient

ANILIST_ENDPOINT = "https://graphql.anilist.co"

class AniListError(RuntimeError):
    """AniList HTTP or GraphQL operation failed."""

class AniListClient:
    def __init__(self, token: str, http: HttpClient | None = None):
        if not token.strip():
            raise ValueError("AniList token is required")
        self._token = token.strip()
        self._http = http or HttpClient()

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.request(
            "POST", ANILIST_ENDPOINT,
            headers={"Authorization": f"Bearer {self._token}",
                     "Content-Type": "application/json", "Accept": "application/json"},
            json={"query": query, "variables": variables or {}},
        )
        if not response.ok:
            raise AniListError(f"AniList returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise AniListError("AniList returned invalid JSON") from exc
        if payload.get("errors"):
            raise AniListError("; ".join(str(e.get("message", "GraphQL error")) for e in payload["errors"]))
        if not isinstance(payload.get("data"), dict):
            raise AniListError("AniList response did not contain a data object")
        return payload["data"]

    def viewer(self) -> dict[str, Any]:
        viewer = self.execute("query { Viewer { id name } }").get("Viewer")
        if not isinstance(viewer, dict):
            raise AniListError("AniList did not return viewer information")
        return viewer
