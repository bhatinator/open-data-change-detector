import pytest
import requests

from watcher.fetcher import FetchError, fetch_page

class FailingSession:
    def get(self, *args, **kwargs):
        raise requests.Timeout("Simulated timeout")

def test_fetch_page_retries_then_reports_error(monkeypatch):
    attempts = []

    class CountingSession:
        def get(self, *args, **kwargs):
            attempts.append(1)
            raise requests.Timeout("Simulated timeout")

    monkeypatch.setattr("watcher.fetcher.time.sleep", lambda _: None)

    with pytest.raises(FetchError):
        fetch_page(
            session=CountingSession(),
            offset=1,
            limit=10,
            max_retries=3,
        )

    assert len(attempts) == 4