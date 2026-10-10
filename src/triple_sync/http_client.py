"""HTTP requests with timeouts and bounded retries for safe/idempotent methods."""
from __future__ import annotations
import random
import time
from typing import Any
import requests
from requests import Response, Session

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}

class HttpClient:
    def __init__(self, *, timeout: float = 20.0, max_retries: int = 3,
                 session: Session | None = None, sleep=time.sleep, random_value=random.random):
        if timeout <= 0 or max_retries < 0:
            raise ValueError("timeout must be positive and max_retries non-negative")
        self.timeout, self.max_retries = timeout, max_retries
        self.session = session or requests.Session()
        self._sleep, self._random = sleep, random_value

    def request(self, method: str, url: str, **kwargs: Any) -> Response:
        kwargs.setdefault("timeout", self.timeout)
        safe = method.upper() in {"GET", "HEAD", "OPTIONS"}
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
            except (requests.Timeout, requests.ConnectionError):
                if not safe or attempt >= self.max_retries:
                    raise
                self._sleep(min(8.0, 0.5 * 2**attempt) + self._random() * 0.1)
                continue
            if response.status_code not in RETRYABLE_STATUS or not safe or attempt >= self.max_retries:
                return response
            try:
                delay = max(0.0, min(30.0, float(response.headers.get("Retry-After", ""))))
            except ValueError:
                delay = min(8.0, 0.5 * 2**attempt) + self._random() * 0.1
            response.close()
            self._sleep(delay)
        raise RuntimeError("HTTP retry loop exited unexpectedly")

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
