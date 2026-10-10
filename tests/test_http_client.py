from unittest.mock import Mock
import requests
from triple_sync.http_client import HttpClient

def test_retries_429_then_succeeds():
    first = Mock(status_code=429, headers={"Retry-After": "0"}, close=Mock())
    second = Mock(status_code=200, headers={})
    session = Mock()
    session.request.side_effect = [first, second]
    client = HttpClient(session=session, max_retries=1, sleep=lambda _: None)
    assert client.request("GET", "https://example.test").status_code == 200
    assert session.request.call_count == 2

def test_post_is_not_retried_automatically():
    session = Mock()
    session.request.return_value = Mock(status_code=503, headers={})
    client = HttpClient(session=session, max_retries=3, sleep=lambda _: None)
    assert client.request("POST", "https://example.test").status_code == 503
    assert session.request.call_count == 1

def test_connection_failure_retries_safe_get():
    session = Mock()
    session.request.side_effect = [requests.ConnectionError("offline"), Mock(status_code=200, headers={})]
    client = HttpClient(session=session, max_retries=1, sleep=lambda _: None)
    assert client.request("GET", "https://example.test").status_code == 200
