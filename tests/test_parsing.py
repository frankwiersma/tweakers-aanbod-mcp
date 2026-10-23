from pathlib import Path

import pytest

from tweakers_aanbod_mcp.parsing import (
    ParseError,
    parse_categories,
    parse_listing,
    parse_price,
    parse_search_page,
)

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.mark.parametrize(
    ("text", "expected"),
    [("€ 375,-", 375), ("€\xa01.249,-", 1249), ("€ 369,95", 369.95), ("N.o.t.k.", None), ("Bieden", None)],
)
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_search_page_reads_counter_and_rows():
    result = parse_search_page(fixture("listing_page.html"), "https://tweakers.net/laptops/aanbod/")

    assert (result.total, result.page, result.pages) == (52, 1, 2)
    first, second = result.listings
    assert first.id == 1000001
    assert first.title == "Example Laptop 14 | i5 | 16GB"
    assert first.price_eur == 1249
    assert first.posted == "dinsdag"
    assert first.summary == "Nette laptop uit de zakelijke lijn, accu prima…"
    assert (first.seller, first.seller_rating, first.seller_reviews) == ("voorbeeldverkoper", 4.5, 168)
    assert (first.city, first.distance_km) == ("Houten", 9)


def test_search_page_handles_open_price_and_unrated_seller():
    second = parse_search_page(fixture("listing_page.html"), "u").listings[1]

    assert second.price_eur is None
    assert second.price_text == "N.o.t.k."
    assert (second.seller, second.seller_rating, second.seller_reviews) == ("nieuwelid", None, 0)
    assert (second.city, second.distance_km) == ("Tilburg", None)


def test_search_page_without_results():
    result = parse_search_page(fixture("listing_empty.html"), "u")

    assert (result.total, result.pages, result.listings) == (0, 0, [])


def test_search_page_rejects_unknown_page():
    with pytest.raises(ParseError):
        parse_search_page("<html><body>Pagina niet gevonden</body></html>", "u")


def test_listing_reads_details_description_and_seller():
    listing = parse_listing(fixture("advertisement.html"))

    assert listing.id == 1000001
    assert listing.title == "Example Laptop 14"
    assert (listing.price_eur, listing.price_text) == (375, "€ 375,-")
    assert listing.condition == "Goed"
    assert listing.age == "36 maanden"
    assert listing.delivery == "ophalen en (pakket)post nationaal"
    assert listing.payment == "contant en betaalverzoek"
    assert (listing.posted_at, listing.views) == ("woensdag 14 oktober 2026 15:46", 1235)
    assert listing.description == "Nette laptop.\nAccu houdt nog 5 uur."
    assert listing.images == ["https://tweakers.net/i/photo1.jpeg", "https://tweakers.net/i/photo2.jpeg"]
    assert listing.pricewatch_url == "https://tweakers.net/pricewatch/123/example-laptop.html"
    seller = listing.seller
    assert seller.location == "1234 AB, Voorbeeldstad, Nederland"
    assert (seller.rating, seller.reviews, seller.total_ads, seller.active_ads) == (4.5, 45, 1142, 4)
    assert seller.member_since == "dinsdag 25 februari 2014 23:25"
    assert seller.company is None


def test_listing_reads_company_from_malformed_business_block():
    listing = parse_listing(fixture("advertisement_business.html"))

    assert listing.shipping_costs == "Inclusief"
    assert listing.seller.company == "Voorbeeld Shop BV"
    assert (listing.seller.rating, listing.seller.reviews) == (5.0, 465)


def test_listing_rejects_removed_advertisement():
    with pytest.raises(ParseError):
        parse_listing("<html><body><h1>Advertentie niet gevonden</h1></body></html>")


def test_categories_are_unique_category_links_only():
    categories = parse_categories(fixture("overview.html"))

    assert [(c.slug, c.name) for c in categories] == [("laptops", "Laptops"), ("videokaarten", "Videokaarten")]
