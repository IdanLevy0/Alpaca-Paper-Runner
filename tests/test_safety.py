import pytest
from runner.alpaca import AlpacaClient, NotPaperError, assert_paper


def test_refuses_live_url():
    with pytest.raises(NotPaperError):
        assert_paper("https://api.alpaca.markets")
    with pytest.raises(NotPaperError):
        AlpacaClient("k", "s", trading_url="https://api.alpaca.markets")


def test_paper_url_ok():
    assert_paper("https://paper-api.alpaca.markets/")
