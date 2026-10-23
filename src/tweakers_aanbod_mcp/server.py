"""MCP server exposing Tweakers Vraag & Aanbod (second-hand listings) as tools."""

import logging
from typing import Annotated

import anyio
import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.runner import serve_loop
from mcp.server.stdio import stdio_server
from mcp_types import ToolAnnotations
from pydantic import Field

from tweakers_aanbod_mcp.client import RateLimitedError, TweakersClient
from tweakers_aanbod_mcp.models import Category, Listing, SearchResult
from tweakers_aanbod_mcp.parsing import ParseError, parse_categories, parse_listing, parse_search_page
from tweakers_aanbod_mcp.query import Condition, SellerType, Sort, search_params

mcp = MCPServer(
    "tweakers-aanbod",
    instructions=(
        "Search second-hand listings on Tweakers Vraag & Aanbod (tweakers.net/aanbod). "
        "Searches are per category: call list_categories to find the slug, then search_listings. "
        "Use get_listing for the full advertisement (description, condition, seller). "
        "Tweakers rate limits busy IPs, so open only the listings you need."
    ),
)
_client = TweakersClient()
_categories: list[Category] = []
_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


async def _fetch(path: str, params: list[tuple[str, str]] | None = None) -> tuple[str, str]:
    try:
        return await _client.get(path, params)
    except RateLimitedError as exc:
        raise ToolError(str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        hint = " (unknown category or listing?)" if exc.response.status_code == 404 else ""
        raise ToolError(f"Tweakers returned HTTP {exc.response.status_code} for {exc.request.url}{hint}") from exc


@mcp.tool(annotations=_READ_ONLY)
async def list_categories(
    contains: Annotated[str | None, Field(description="Case-insensitive text to match in slug or name.")] = None,
) -> list[Category]:
    """List Vraag & Aanbod categories (about 220, e.g. laptops, videokaarten, cameras)."""
    if not _categories:
        html, _ = await _fetch("/aanbod/")
        _categories.extend(parse_categories(html))
    if not contains:
        return _categories
    needle = contains.lower()
    return [c for c in _categories if needle in c.slug or needle in c.name.lower()]


@mcp.tool(annotations=_READ_ONLY)
async def search_listings(
    category: Annotated[str, Field(description="Category slug from list_categories, e.g. 'laptops'.")],
    keyword: Annotated[str | None, Field(description="Words that must appear in the listing.")] = None,
    min_price: Annotated[int | None, Field(description="Minimum asking price in euros.")] = None,
    max_price: Annotated[int | None, Field(description="Maximum asking price in euros.")] = None,
    near: Annotated[
        str | None,
        Field(
            description="Place name ('Utrecht') or full Dutch postcode ('3521DT'). Adds the distance to each "
            "listing. A 4-digit postcode alone may resolve to Belgium."
        ),
    ] = None,
    max_distance_km: Annotated[int | None, Field(description="Only listings within this distance of `near`.")] = None,
    conditions: Annotated[list[Condition] | None, Field(description="Keep only these conditions.")] = None,
    seller_type: Annotated[SellerType | None, Field(description="Private sellers or businesses only.")] = None,
    min_seller_rating: Annotated[int | None, Field(description="Minimum seller rating, 1 to 5 stars.")] = None,
    sort: Sort = "newest",
    page: Annotated[int, Field(ge=1, description="Result page; each page holds about 40 listings.")] = 1,
    include_wanted: Annotated[bool, Field(description="Also return 'gevraagd' (wanted) posts.")] = False,
) -> SearchResult:
    """Search one Vraag & Aanbod category. Filtering happens on Tweakers' side, so narrow filters
    cost no extra requests. Returns about 40 listings per page with price, seller rating and city."""
    if not category.replace("-", "").isalnum():
        raise ToolError(f"invalid category slug {category!r}; use list_categories")
    try:
        params = search_params(
            keyword=keyword,
            min_price=min_price,
            max_price=max_price,
            near=near,
            max_distance_km=max_distance_km,
            conditions=conditions,
            seller_type=seller_type,
            min_seller_rating=min_seller_rating,
            sort=sort,
            page=page,
            include_wanted=include_wanted,
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    html, url = await _fetch(f"/{category}/aanbod/", params)
    try:
        result = parse_search_page(html, url)
    except ParseError as exc:
        raise ToolError(f"{exc} ({url}); check the category slug with list_categories") from exc
    # Tweakers ignores a place it cannot resolve and returns the unfiltered category.
    if near and result.listings and all(listing.distance_km is None for listing in result.listings):
        raise ToolError(f"Tweakers did not recognise the place {near!r}; try a plain place name or a full postcode")
    return result


@mcp.tool(annotations=_READ_ONLY)
async def get_listing(
    listing_id: Annotated[int, Field(description="The `id` from search_listings, or the number in /aanbod/<id>/.")],
) -> Listing:
    """Open one advertisement: full description, condition, warranty, age, delivery and payment options,
    photos, and the seller's location, rating and history. Old ids still resolve, so check `posted_at`."""
    html, url = await _fetch(f"/aanbod/{listing_id}/")
    try:
        return parse_listing(html)
    except ParseError as exc:
        raise ToolError(f"{exc} ({url})") from exc


async def _serve_stdio() -> None:
    # Claude Code opens with a 2026-07-28 `server/discover` probe and then sends the 2025 `initialize`
    # handshake on the same connection. MCPServer.run() locks a connection to the era of its first
    # request and refuses that handshake (-32022), so serve the handshake era: the probe gets an
    # error and the client carries on with `initialize`.
    server = mcp._lowlevel_server
    async with stdio_server() as (read_stream, write_stream), server.lifespan(server) as lifespan_state:
        await serve_loop(
            server,
            read_stream,
            write_stream,
            lifespan_state=lifespan_state,
            init_options=server.create_initialization_options(),
        )


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    anyio.run(_serve_stdio)
