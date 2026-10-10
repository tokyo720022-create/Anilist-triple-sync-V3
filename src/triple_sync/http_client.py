"""HTTP requests with timeouts and bounded retries for safe/idempotent operations."""
from __future__ import annotations

import random
import time
from typing import Any

import requests
from requests import Response, Session

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class HttpClient:
    def __init__(
        self,
        *,
        timeout: float = 20.0,
        max_retries: int = 3,
        session: Session | None = None,
        sleep=time.sleep,
        random_value=random.random,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self._sleep = sleep
        self._random = random_value

    def request(
        self,
        method: str,
        url: str,
        *,
        retryable: bool | None = None,
        **kwargs: Any,
    ) -> Response:
        kwargs.setdefault("timeout", self.timeout)
        can_retry = method.upper() in SAFE_METHODS if retryable is None else retryable

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
            except (requests.Timeout, requests.ConnectionError):
                if not can_retry or attempt >= self.max_retries:
                    raise
                delay = min(8.0, 0.5 * (2**attempt)) + self._random() * 0.1
                self._sleep(delay)
                continue

            if response.status_code not in RETRYABLE_STATUS or not can_retry or attempt >= self.max_retries:
                return response

            try:
                delay = max(0.0, min(30.0, float(response.headers.get("Retry-After", ""))))
            except (TypeError, ValueError):
                delay = min(8.0, 0.5 * (2**attempt)) + self._random() * 0.1
            response.close()
            self._sleep(delay)

        raise RuntimeError("HTTP retry loop exited unexpectedly")

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
