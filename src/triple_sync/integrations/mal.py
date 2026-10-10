"""MAL OAuth refresh adapter; list synchronization is a later milestone."""
from typing import Any
from requests.auth import HTTPBasicAuth
from triple_sync.http_client import HttpClient

MAL_TOKEN_ENDPOINT = "https://myanimelist.net/v1/oauth2/token"

class MyAnimeListError(RuntimeError):
    """MAL OAuth request failed."""

def refresh_access_token(client_id: str, client_secret: str, refresh_token: str,
                         *, http: HttpClient | None = None) -> dict[str, Any]:
    values = [client_id.strip(), client_secret.strip(), refresh_token.strip()]
    if not all(values):
        raise ValueError("MAL client ID, client secret, and refresh token are required")
    client = http or HttpClient()
    response = client.request(
        "POST", MAL_TOKEN_ENDPOINT,
        auth=HTTPBasicAuth(values[0], values[1]),
        data={"grant_type": "refresh_token", "refresh_token": values[2]},
        headers={"Accept": "application/json"},
    )
    if not response.ok:
        raise MyAnimeListError(f"MAL token endpoint returned HTTP {response.status_code}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise MyAnimeListError("MAL token endpoint returned invalid JSON") from exc
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise MyAnimeListError("MAL token response did not include an access token")
    return payload
