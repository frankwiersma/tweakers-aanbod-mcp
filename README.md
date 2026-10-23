# tweakers-aanbod-mcp

MCP server for [Tweakers Vraag & Aanbod](https://tweakers.net/aanbod/), the Dutch second-hand
marketplace for electronics. It lets Claude (or any MCP client) search listings in a category,
filter on price, condition, seller type and distance, and open a single advertisement.

> "Find laptops between €300 and €550 within 30 km of Utrecht, nearest first, and open the best one."

For new products and shop prices, see [rleroi/tweakers-mcp](https://github.com/rleroi/tweakers-mcp)
(Pricewatch). This server covers the second-hand side.

## Install

Needs [uv](https://docs.astral.sh/uv/) (`brew install uv`).

**Claude Code**

```bash
claude mcp add tweakers-aanbod -- uvx --from git+https://github.com/frankwiersma/tweakers-aanbod-mcp tweakers-aanbod-mcp
```

**Claude Desktop**: add this to `~/Library/Application Support/Claude/claude_desktop_config.json`
(Windows: `%APPDATA%\Claude\claude_desktop_config.json`) and restart Claude Desktop. Desktop does not
use your shell `PATH`, so use the absolute path from `which uvx`:

```json
{
  "mcpServers": {
    "tweakers-aanbod": {
      "command": "/absolute/path/to/uvx",
      "args": ["--from", "git+https://github.com/frankwiersma/tweakers-aanbod-mcp", "tweakers-aanbod-mcp"]
    }
  }
}
```

## Tools

| Tool | What it does |
| --- | --- |
| `list_categories(contains)` | The ~220 Vraag & Aanbod categories with their slugs (`laptops`, `videokaarten`, ...) |
| `search_listings(category, ...)` | One page (~40 listings) of a category: title, price, date, seller rating, city, distance |
| `get_listing(listing_id)` | The full advertisement: description, condition, warranty, age, delivery, payment, photos, seller |

`search_listings` filters on Tweakers' side, so a narrow search costs one request:

| Argument | Example | Notes |
| --- | --- | --- |
| `keyword` | `"thinkpad t14"` | |
| `min_price`, `max_price` | `300`, `550` | Euros |
| `near`, `max_distance_km` | `"Utrecht"`, `30` | Place name or full Dutch postcode (`3521DT`). Each listing then carries `distance_km`. |
| `conditions` | `["new", "good"]` | `new`, `good`, `visibly_used`, `defective` |
| `seller_type` | `"business"` | `private` or `business` |
| `min_seller_rating` | `4` | 1 to 5 stars |
| `sort` | `"price_low"` | `newest`, `oldest`, `price_low`, `price_high`, `nearest`, `best_rated` |
| `page` | `2` | |
| `include_wanted` | `true` | Also return "gevraagd" posts |

## How it works

It reads the same public pages a browser does: the category listing at `/<category>/aanbod/` (with
the query parameters of its filter form) and the advertisement at `/aanbod/<id>/`. It stays out of
the paths that `robots.txt` disallows (`/aanbod/zoeken`, `/ajax`, ...), which is why every search
needs a category.

Requests go out one at a time, at least two seconds apart. Tweakers rate limits busy IPs; when that
happens the tool returns a clear error and you can retry after a minute. Nothing is cached to disk
or stored.

## Caveats

- Unofficial and not affiliated with Tweakers. It parses HTML, which can change at any time.
- Listings include seller nicknames and locations as Tweakers shows them. Tweakers' terms do not
  allow collecting other members' personal data systematically, so use this for your own searches,
  not for building datasets.
- Tweakers ignores a place name it cannot resolve. The tool detects that and returns an error
  instead of unfiltered results.
- An old listing id still opens; check `posted_at`.

## Development

```bash
git clone https://github.com/frankwiersma/tweakers-aanbod-mcp && cd tweakers-aanbod-mcp
uv sync
uv run pytest                # offline, against fixtures in tests/fixtures
uv run tweakers-aanbod-mcp   # stdio server
```

MIT licensed.
