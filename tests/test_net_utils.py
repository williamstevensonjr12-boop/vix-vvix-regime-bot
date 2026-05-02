"""
test_net_utils.py — pytest unit tests for the shared HTTP resilience helpers.

These cover the install_default_timeout patch and the with_retry wrapper.
Both are now in the hot path of every Alpaca SDK call, so a silent regression
here would re-introduce the crash class the timeout+retry fix was built to
prevent.

Run from repo/:
    pytest tests/test_net_utils.py -v
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import net_utils


# ── install_default_timeout ──────────────────────────────────────────────────

class TestInstallDefaultTimeout:
    def _make_fake_client(self):
        """Stand-in for an SDK client with a requests.Session-like _session."""
        client = MagicMock()
        session = MagicMock()
        session.request = MagicMock(return_value="response")
        # MagicMock's auto-attribute creation would fool getattr(..., False);
        # explicitly set the marker to False so the patcher treats it as fresh.
        session._alpaca_timeout_patched = False
        client._session = session
        return client, session

    def test_injects_default_timeout_when_caller_omits(self):
        client, session = self._make_fake_client()
        original = session.request
        net_utils.install_default_timeout(client)

        # Calling without a timeout should pick up the default
        client._session.request("GET", "https://example.com/v2/account")

        original.assert_called_once_with(
            "GET", "https://example.com/v2/account", timeout=net_utils.REQUEST_TIMEOUT_SEC
        )

    def test_respects_caller_provided_timeout(self):
        client, session = self._make_fake_client()
        original = session.request
        net_utils.install_default_timeout(client)

        client._session.request("GET", "https://example.com/clock", timeout=5.0)

        original.assert_called_once_with(
            "GET", "https://example.com/clock", timeout=5.0
        )

    def test_idempotent_does_not_double_patch(self):
        client, session = self._make_fake_client()
        net_utils.install_default_timeout(client)
        first_wrapped = client._session.request

        # Second call should be a no-op (already patched)
        net_utils.install_default_timeout(client)
        assert client._session.request is first_wrapped

    def test_safe_when_session_missing(self):
        # Some SDK builds may lack _session — never raise
        client = MagicMock(spec=[])  # no _session attribute
        net_utils.install_default_timeout(client)  # must not raise


# ── with_retry ────────────────────────────────────────────────────────────────

class TestWithRetry:
    def test_returns_value_on_first_success(self):
        fn = MagicMock(return_value="ok")
        with patch("net_utils._time.sleep") as sleep:
            result = net_utils.with_retry("label", fn, "arg1", kw="v")
        assert result == "ok"
        fn.assert_called_once_with("arg1", kw="v")
        sleep.assert_not_called()

    def test_retries_on_connection_error_then_succeeds(self):
        fn = MagicMock(side_effect=[
            requests.exceptions.ConnectionError("reset"),
            "ok",
        ])
        with patch("net_utils._time.sleep") as sleep:
            result = net_utils.with_retry("label", fn)
        assert result == "ok"
        assert fn.call_count == 2
        assert sleep.call_count == 1

    def test_retries_on_timeout(self):
        fn = MagicMock(side_effect=[
            requests.exceptions.Timeout("read timed out"),
            "ok",
        ])
        with patch("net_utils._time.sleep"):
            result = net_utils.with_retry("label", fn)
        assert result == "ok"
        assert fn.call_count == 2

    def test_retries_on_chunked_encoding_error(self):
        fn = MagicMock(side_effect=[
            requests.exceptions.ChunkedEncodingError("partial body"),
            "ok",
        ])
        with patch("net_utils._time.sleep"):
            result = net_utils.with_retry("label", fn)
        assert result == "ok"
        assert fn.call_count == 2

    def test_reraises_after_max_retries(self):
        # MAX_RETRIES retries means MAX_RETRIES+1 total attempts before re-raise
        err = requests.exceptions.ConnectionError("persistent")
        fn = MagicMock(side_effect=[err] * (net_utils.MAX_RETRIES + 1))
        with patch("net_utils._time.sleep"):
            with pytest.raises(requests.exceptions.ConnectionError):
                net_utils.with_retry("label", fn)
        assert fn.call_count == net_utils.MAX_RETRIES + 1

    def test_does_not_retry_on_non_retryable(self):
        fn = MagicMock(side_effect=ValueError("bad input"))
        with patch("net_utils._time.sleep") as sleep:
            with pytest.raises(ValueError):
                net_utils.with_retry("label", fn)
        fn.assert_called_once()
        sleep.assert_not_called()

    def test_backoff_grows_exponentially(self):
        # Force jitter to a constant 1.0 (i.e. 0.5 + random()=0.5 → 1.0) so we
        # can assert the exponential progression without flakiness.
        err = requests.exceptions.ConnectionError("x")
        fn = MagicMock(side_effect=[err, err, err, "ok"])
        with patch("net_utils._time.sleep") as sleep, \
             patch("net_utils.random.random", return_value=0.5):
            net_utils.with_retry("label", fn)

        # Expected sleeps: BASE * 2^(attempt-1) * (0.5 + 0.5) = BASE * 2^0, 2^1, 2^2
        expected = [
            net_utils.BASE_BACKOFF_SEC * (2 ** 0),
            net_utils.BASE_BACKOFF_SEC * (2 ** 1),
            net_utils.BASE_BACKOFF_SEC * (2 ** 2),
        ]
        actual = [c.args[0] for c in sleep.call_args_list]
        assert actual == pytest.approx(expected)
