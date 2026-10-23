import asyncio

import httpx
import pytest

from tweakers_aanbod_mcp.client import BASE_URL, RateLimitedError, TweakersClient


def client_returning(status: int, requests: list[httpx.Request]) -> TweakersClient:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, text="<html></html>")

    http = httpx.AsyncClient(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return TweakersClient(http, min_interval=0)


def test_get_returns_html_and_url_with_repeated_params():
    requests: list[httpx.Request] = []
    client = client_returning(200, requests)

    html, url = asyncio.run(client.get("/laptops/aanbod/", [("vat", "a"), ("vat", "v")]))

    assert html == "<html></html>"
    assert url == "https://tweakers.net/laptops/aanbod/?vat=a&vat=v"


def test_rate_limit_becomes_a_clear_error():
    client = client_returning(429, [])

    with pytest.raises(RateLimitedError, match="Wait a minute"):
        asyncio.run(client.get("/aanbod/"))


def test_requests_are_spaced_out():
    http = httpx.AsyncClient(base_url=BASE_URL, transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    client = TweakersClient(http, min_interval=0.2)

    async def two_requests() -> float:
        loop = asyncio.get_running_loop()
        start = loop.time()
        await asyncio.gather(client.get("/a/"), client.get("/b/"))
        return loop.time() - start

    assert asyncio.run(two_requests()) >= 0.2
