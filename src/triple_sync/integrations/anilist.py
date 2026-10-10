"""AniList GraphQL client with conservative retry handling."""
from __future__ import annotations

import re
from typing import Any

from triple_sync.http_client import HttpClient

ANILIST_ENDPOINT = "https://graphql.anilist.co"


class AniListError(RuntimeError):
    """AniList HTTP or GraphQL operation failed."""


def _is_read_only_operation(query: str) -> bool:
    """Return whether the GraphQL operation is a query rather than a mutation."""
    statement = re.sub(r"(?m)^\s*#.*$", "", query).lstrip()
    if statement.startswith("{"):
        return True  # GraphQL shorthand syntax always denotes a query.
    match = re.match(r"(query|mutation|subscription)\b", statement)
    return match is None or match.group(1) == "query"


class AniListClient:
    def __init__(self, token: str | None = None, http: HttpClient | None = None) -> None:
        self._token = (token or "").strip()
        self._http = http or HttpClient()

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        response = self._http.request(
            "POST",
            ANILIST_ENDPOINT,
            retryable=_is_read_only_operation(query),
            headers=headers,
            json={"query": query, "variables": variables or {}},
        )
        if not response.ok:
            raise AniListError(f"AniList returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise AniListError("AniList returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise AniListError("AniList returned an unexpected response")
        if payload.get("errors"):
            messages = [
                str(item.get("message", "GraphQL error"))
                for item in payload["errors"]
                if isinstance(item, dict)
            ]
            raise AniListError("; ".join(messages) or "AniList GraphQL operation failed")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise AniListError("AniList response did not contain a data object")
        return data

    def viewer(self) -> dict[str, Any]:
        viewer = self.execute("query { Viewer { id name } }").get("Viewer")
        if not isinstance(viewer, dict):
            raise AniListError("AniList did not return viewer information")
        return viewer
