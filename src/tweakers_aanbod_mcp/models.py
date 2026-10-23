"""Data returned by the MCP tools."""

from pydantic import BaseModel, Field


class Category(BaseModel):
    """A Vraag & Aanbod category, addressed by its slug."""

    slug: str = Field(description="Use this value as `category` in search_listings, e.g. 'laptops'.")
    name: str


class ListingSummary(BaseModel):
    """One row of a category listing page."""

    id: int
    title: str
    url: str
    price_eur: float | None = Field(description="Asking price; null when the price is open ('N.o.t.k.', 'Bieden').")
    price_text: str
    posted: str = Field(description="Relative date as Tweakers shows it, e.g. '15 uur geleden' or '3 okt'.")
    summary: str
    seller: str
    seller_rating: float | None = Field(description="Average rating out of 5.")
    seller_reviews: int
    city: str | None
    distance_km: int | None = Field(description="Only set when the search used `near`.")


class SearchResult(BaseModel):
    """One page of search results."""

    url: str
    total: int
    page: int
    pages: int
    listings: list[ListingSummary]


class Seller(BaseModel):
    name: str
    profile_url: str | None
    location: str | None = Field(description="As shown on Tweakers, e.g. '1817 BA, Alkmaar, Nederland'.")
    rating: float | None
    reviews: int
    total_ads: int | None
    active_ads: int | None
    member_since: str | None
    company: str | None = Field(description="Company name for business sellers.")


class Listing(BaseModel):
    """The full advertisement."""

    id: int
    title: str
    url: str
    price_eur: float | None
    price_text: str
    shipping_costs: str | None
    condition: str | None
    warranty: str | None
    age: str | None
    delivery: str | None = Field(description="How the item changes hands, e.g. 'ophalen en (pakket)post nationaal'.")
    payment: str | None
    posted_at: str | None
    views: int | None
    description: str
    images: list[str]
    pricewatch_url: str | None = Field(description="Linked Pricewatch product, if the seller picked one.")
    seller: Seller
