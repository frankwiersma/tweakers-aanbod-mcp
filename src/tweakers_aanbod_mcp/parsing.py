"""Turn Tweakers Vraag & Aanbod HTML into models. Pure functions, no network."""

import re

from bs4 import BeautifulSoup, Tag

from tweakers_aanbod_mcp.models import Category, Listing, ListingSummary, SearchResult, Seller

_AD_ID = re.compile(r"/aanbod/(\d+)/")
_CATEGORY_URL = re.compile(r"^https://tweakers\.net/([a-z0-9-]+)/aanbod/$")


class ParseError(ValueError):
    """The page does not look like the Tweakers page we expected."""


def parse_price(text: str) -> float | None:
    """Parse '€ 1.250,-' or '€ 369,95' to a number; None for open prices like 'N.o.t.k.'."""
    match = re.search(r"€\s*([\d.]+)(?:,(\d{2}|-))?", text)
    if not match:
        return None
    euros = int(match.group(1).replace(".", ""))
    cents = match.group(2)
    return euros + (int(cents) / 100 if cents and cents != "-" else 0)


def parse_categories(html: str) -> list[Category]:
    """Read the category links from the /aanbod/ overview page."""
    soup = BeautifulSoup(html, "html.parser")
    categories: dict[str, Category] = {}
    for link in soup.select("a[href]"):
        match = _CATEGORY_URL.match(link["href"])
        name = link.get_text(" ", strip=True)
        if match and name and match.group(1) not in categories:
            categories[match.group(1)] = Category(slug=match.group(1), name=name)
    if not categories:
        raise ParseError("no categories found on the Vraag & Aanbod overview page")
    return list(categories.values())


def parse_search_page(html: str, url: str) -> SearchResult:
    """Read one page of a category listing."""
    soup = BeautifulSoup(html, "html.parser")
    page_index = soup.select_one("div.pageIndex")
    if page_index is None:
        if "geen advertenties gevonden" in soup.get_text():
            return SearchResult(url=url, total=0, page=1, pages=0, listings=[])
        raise ParseError("no result counter on the listing page")
    match = re.search(r"([\d.]+) advertenties? - Pagina (\d+) van (\d+)", page_index.get_text(" ", strip=True))
    if not match:
        raise ParseError(f"unexpected result counter: {page_index.get_text(' ', strip=True)!r}")
    rows = [row for row in soup.select("table.listing tr") if row.select_one("p.title a")]
    return SearchResult(
        url=url,
        total=int(match.group(1).replace(".", "")),
        page=int(match.group(2)),
        pages=int(match.group(3)),
        listings=[_parse_row(row) for row in rows],
    )


def _parse_row(row: Tag) -> ListingSummary:
    link = row.select_one("p.title a")
    lead = row.select_one("p.lead")
    date = lead.select_one("span.date") if lead else None
    posted = date.get_text(strip=True) if date else ""
    lead_text = lead.get_text(" ", strip=True) if lead else ""
    summary = lead_text.removeprefix(posted).lstrip(" -")

    seller_cell = row.select_one("td.location:not(.city)")
    seller_text = seller_cell.select_one("p.subtitle").get_text(strip=True) if seller_cell else ""
    stars = seller_cell.select_one("twk-star-rating") if seller_cell else None
    reviews = re.search(r"(\d+) beoordeling", stars.get("title", "")) if stars else None

    city_cell = row.select_one("td.city")
    city = city_cell.select_one("p.ellipsis") if city_cell else None
    distance = city_cell.select_one("p.subtitle") if city_cell else None
    distance_km = re.search(r"(\d+)\s*km", distance.get_text()) if distance else None

    price_text = _clean(row.select_one("td.vaprice").get_text(" ", strip=True))
    return ListingSummary(
        id=int(_AD_ID.search(link["href"]).group(1)),
        title=link.get("title") or link.get_text(strip=True),
        url=link["href"],
        price_eur=parse_price(price_text),
        price_text=price_text,
        posted=posted,
        summary=summary,
        seller=re.sub(r"\s*\(\d+\)$", "", seller_text),
        seller_rating=_parse_score(stars) if reviews and reviews.group(1) != "0" else None,
        seller_reviews=int(reviews.group(1)) if reviews else 0,
        city=city.get_text(strip=True) if city else None,
        distance_km=int(distance_km.group(1)) if distance_km else None,
    )


def parse_listing(html: str) -> Listing:
    """Read a single advertisement page."""
    soup = BeautifulSoup(html, "html.parser")
    ad = soup.select_one("div.vaAdvertisement")
    if ad is None:
        raise ParseError("no advertisement on this page; it may have been removed")

    canonical = soup.select_one("link[rel=canonical]")
    url = canonical["href"] if canonical else ""
    details = {row.th.get_text(strip=True): row.td for row in ad.select("table.adDetails tr") if row.th and row.td}
    price_text = _cell_text(details, "Vraagprijs") or ""

    author = ad.select_one("p.author")
    author_text = author.get_text(" ", strip=True) if author else ""
    posted = re.search(r",\s*(\w+dag \d+ \w+ \d{4} \d{1,2}:\d{2})", author_text)
    views = re.search(r"([\d.]+)\s*views", author_text)

    description = ad.select_one("#advertisementDescription .ugcContent")
    pricewatch = ad.select_one(".specLink a")
    return Listing(
        id=int(_AD_ID.search(url).group(1)) if _AD_ID.search(url) else 0,
        title=re.sub(r"\s+(aangeboden|gevraagd)$", "", soup.select_one("h1").get_text(" ", strip=True)),
        url=url,
        price_eur=parse_price(price_text),
        price_text=price_text,
        shipping_costs=_cell_text(details, "Verzendkosten"),
        condition=_cell_text(details, "Staat"),
        warranty=_cell_text(details, "Garantie"),
        age=_cell_text(details, "Leeftijd"),
        delivery=_cell_text(details, "Verzending"),
        payment=_cell_text(details, "Betaling"),
        posted_at=posted.group(1) if posted else None,
        views=int(views.group(1).replace(".", "")) if views else None,
        description=description.get_text("\n", strip=True) if description else "",
        images=[link["href"] for link in ad.select(".imageCarousel a.thumb[href]")],
        pricewatch_url=pricewatch["href"] if pricewatch else None,
        seller=_parse_seller(ad),
    )


def _parse_seller(ad: Tag) -> Seller:
    block = ad.select_one("dl.adverteerder").find_parent("div", class_="adDetails")
    fields = {dt.get_text(strip=True): dd for dt in block.select("dt") if (dd := dt.find_next_sibling("dd"))}
    name = fields["Naam"]
    profile = name.select_one("a[href]")
    rating = fields.get("Beoordeling")
    reviews = re.search(r"\((\d+)\)", rating.get_text(" ", strip=True)) if rating else None
    history = fields.get("History")
    total_ads = re.search(r"([\d.]+) advertentie", history.get_text(" ", strip=True)) if history else None
    active_ads = re.search(r"([\d.]+) actief", history.get_text(" ", strip=True)) if history else None
    return Seller(
        name=name.get_text(strip=True),
        profile_url=profile["href"] if profile else None,
        location=_cell_text(fields, "Locatie"),
        rating=_parse_score(rating.select_one("twk-star-rating")) if reviews and reviews.group(1) != "0" else None,
        reviews=int(reviews.group(1)) if reviews else 0,
        total_ads=int(total_ads.group(1).replace(".", "")) if total_ads else None,
        active_ads=int(active_ads.group(1).replace(".", "")) if active_ads else None,
        member_since=_cell_text(fields, "Actief sinds"),
        company=fields["Bedrijfsnaam"].get("title") if "Bedrijfsnaam" in fields else None,
    )


def _parse_score(stars: Tag | None) -> float | None:
    if stars is None:
        return None
    match = re.match(r"([\d.]+)\s*/\s*5", stars.get("data-score", ""))
    return float(match.group(1)) if match else None


def _cell_text(cells: dict[str, Tag], key: str) -> str | None:
    cell = cells.get(key)
    return _clean(cell.get_text(" ", strip=True)) if cell else None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
