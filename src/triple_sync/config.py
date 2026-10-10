"""Environment-backed configuration with explicit validation."""
from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(ValueError):
    """Required environment configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    anilist_token: str = ""
    anilist_username: str = "Orewatokyo"
    mal_client_id: str = ""
    mal_client_secret: str = ""
    mal_refresh_token: str = ""
    request_timeout_seconds: float = 20.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            timeout = float(os.getenv("TRIPLE_SYNC_TIMEOUT", "20"))
            retries = int(os.getenv("TRIPLE_SYNC_RETRIES", "3"))
        except ValueError as exc:
            raise ConfigurationError("Timeout and retry settings must be numeric.") from exc
        if timeout <= 0:
            raise ConfigurationError("TRIPLE_SYNC_TIMEOUT must be greater than zero.")
        if not 0 <= retries <= 8:
            raise ConfigurationError("TRIPLE_SYNC_RETRIES must be between 0 and 8.")
        username = os.getenv("ANILIST_USERNAME", "Orewatokyo").strip()
        if not username:
            raise ConfigurationError("ANILIST_USERNAME must not be empty.")
        return cls(
            anilist_token=os.getenv("ANILIST_TARGET_TOKEN", "").strip(),
            anilist_username=username,
            mal_client_id=os.getenv("MAL_CLIENT_ID", "").strip(),
            mal_client_secret=os.getenv("MAL_CLIENT_SECRET", "").strip(),
            mal_refresh_token=os.getenv("MAL_REFRESH_TOKEN", "").strip(),
            request_timeout_seconds=timeout,
            max_retries=retries,
        )

    def missing_for_sync(self) -> list[str]:
        values = {
            "ANILIST_TARGET_TOKEN": self.anilist_token,
            "MAL_CLIENT_ID": self.mal_client_id,
            "MAL_CLIENT_SECRET": self.mal_client_secret,
            "MAL_REFRESH_TOKEN": self.mal_refresh_token,
        }
        return [name for name, value in values.items() if not value]
