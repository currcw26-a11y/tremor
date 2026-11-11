import requests

from tremor import db


def test_a_dropped_connection_is_tried_again(monkeypatch):
    calls = []

    def flaky(method, url, **kw):
        calls.append(method)
        if len(calls) == 1:
            raise requests.ConnectionError("Remote end closed connection without response")
        return "ok"

    monkeypatch.setattr(db._session, "request", flaky)
    monkeypatch.setattr(db.time, "sleep", lambda s: None)
    assert db._send("POST", "https://example.invalid") == "ok"
    assert calls == ["POST", "POST"]
