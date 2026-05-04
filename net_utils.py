"""
net_utils.py — Shared HTTP resilience helpers for Alpaca SDK clients.

The Alpaca SDK (TradingClient, StockHistoricalDataClient) leaves request
timeout=None on its underlying requests.Session. A hung TCP connection then
blocks indefinitely until the OS gives up — that was the source of the
ReadTimeout crash storm and the silent hangs the watchdog kept SIGTERM'ing.

Every SDK client this project creates should be passed through
install_default_timeout(), and frequently-called read-only methods should be
wrapped in with_retry() so transient network errors do not crash the bot.

Intentionally NOT wrapping order submission — retrying a placed order risks
duplicate fills.
"""
from __future__ import annotations
import logging
import random
import time as _time

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SEC = (10.0, 20.0)  # (connect, read)
# 6 retries → ~63s base sleep budget (1+2+4+8+16+32) plus jitter, comfortably
# under hang_watchdog's 180s SIGTERM ceiling. Bumped from 4 on 2026-05-04 after
# observing overnight DNS-failure crash storms tied to laptop sleep/wake — the
# 4-retry budget (~31s) was marginally too short for macOS DNS to recover.
MAX_RETRIES = 6
BASE_BACKOFF_SEC = 1.0
RETRYABLE_EXC = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


def install_default_timeout(client) -> None:
    """Patch the SDK's underlying requests.Session so every call has a timeout."""
    session = getattr(client, "_session", None)
    if session is None or getattr(session, "_alpaca_timeout_patched", False):
        return
    original_request = session.request

    def request_with_timeout(method, url, **kwargs):
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_SEC)
        return original_request(method, url, **kwargs)

    session.request = request_with_timeout
    session._alpaca_timeout_patched = True


def with_retry(label: str, fn, *args, **kwargs):
    """Call fn with retries on transient network errors. Re-raises on final failure."""
    attempt = 0
    while True:
        try:
            return fn(*args, **kwargs)
        except RETRYABLE_EXC as e:
            attempt += 1
            if attempt > MAX_RETRIES:
                logger.error(f"{label} failed after {MAX_RETRIES} retries: {e}")
                raise
            sleep_for = BASE_BACKOFF_SEC * (2 ** (attempt - 1))
            sleep_for *= 0.5 + random.random()  # jitter
            logger.warning(
                f"{label} transient error (attempt {attempt}/{MAX_RETRIES}): "
                f"{type(e).__name__}: {e}. Retrying in {sleep_for:.1f}s."
            )
            _time.sleep(sleep_for)
