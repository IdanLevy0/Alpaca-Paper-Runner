"""Secrets must never reach the committed log, and pasted line breaks must not break the client."""
import requests

from runner import run as R
from runner.alpaca import AlpacaClient


def test_keys_are_stripped(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", " PKTESTKEY123\n")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "SECRETVALUE987654\r\n")
    c = AlpacaClient.from_env()
    assert c.s.headers["APCA-API-KEY-ID"] == "PKTESTKEY123"
    assert c.s.headers["APCA-API-SECRET-KEY"] == "SECRETVALUE987654"


def test_header_error_hides_value(monkeypatch):
    monkeypatch.setenv("ALPACA_SECRET_KEY", "SECRETVALUE987654")
    e = requests.exceptions.InvalidHeader("Invalid leading whitespace in header value: 'SECRETVALUE987654\\n'")
    assert "SECRETVALUE987654" not in R.safe_error(e)


def test_other_errors_redacted(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "PKTESTKEY123")
    assert "PKTESTKEY123" not in R.safe_error(RuntimeError("401 for key PKTESTKEY123"))
