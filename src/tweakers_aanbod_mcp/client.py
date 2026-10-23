"""HTTP access to tweakers.net, spaced out so we stay a polite visitor."""

import asyncio
import time

import httpx

BASE_URL = "https://tweakers.net"
USER_AGENT = "tweakers-aanbod-mcp/0.1 (+https://github.com/frankwiersma/tweakers-aanbod-mcp)"


class RateLimitedError(RuntimeError):
    """Tweakers answered 429: too many page views from this IP."""


class TweakersClient:
    """Fetches pages one at a time, at least `min_interval` seconds apart."""

    def __init__(self, http: httpx.AsyncClient | None = None, min_interval: float = 2.0):
        self._http = http or httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "nl-NL,nl;q=0.9"},
            follow_redirects=True,
            timeout=20,
        )
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def get(self, path: str, params: list[tuple[str, str]] | None = None) -> tuple[str, str]:
        """Return the page HTML and its final URL."""
        async with self._lock:
            wait = self._last_request + self._min_interval - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                response = await self._http.get(path, params=params)
            finally:
                self._last_request = time.monotonic()
        if response.status_code == 429:
            raise RateLimitedError(
                "Tweakers is rate limiting this IP (HTTP 429). Wait a minute and try again with fewer requests."
            )
        response.raise_for_status()
        return response.text, str(response.url)
