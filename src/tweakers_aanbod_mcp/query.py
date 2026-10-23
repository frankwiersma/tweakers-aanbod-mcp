"""Map tool arguments onto the query parameters of a Tweakers category listing."""

from typing import Literal

Condition = Literal["new", "good", "visibly_used", "defective"]
SellerType = Literal["private", "business"]
Sort = Literal["newest", "oldest", "price_low", "price_high", "nearest", "best_rated"]

_CONDITIONS: dict[Condition, str] = {
    "new": "nieuw",
    "good": "goede staat",
    "visibly_used": "gebruikssporen",
    "defective": "defect",
}
_SELLER_TYPES: dict[SellerType, str] = {"private": "personal", "business": "business"}
_SORTS: dict[Sort, tuple[str, str]] = {
    "newest": ("time", "desc"),
    "oldest": ("time", "asc"),
    "price_low": ("prijs", "asc"),
    "price_high": ("prijs", "desc"),
    "nearest": ("distance", "asc"),
    "best_rated": ("rating", "desc"),
}


def search_params(
    *,
    keyword: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    near: str | None = None,
    max_distance_km: int | None = None,
    conditions: list[Condition] | None = None,
    seller_type: SellerType | None = None,
    min_seller_rating: int | None = None,
    sort: Sort = "newest",
    page: int = 1,
    include_wanted: bool = False,
) -> list[tuple[str, str]]:
    """Build the query string, as a list because Tweakers repeats keys for multi-select filters."""
    if sort == "nearest" and not near:
        raise ValueError("sort='nearest' needs `near`")
    if max_distance_km is not None and not near:
        raise ValueError("max_distance_km needs `near`")
    if min_seller_rating is not None and not 1 <= min_seller_rating <= 5:
        raise ValueError("min_seller_rating must be between 1 and 5")

    params: list[tuple[str, str]] = [("vat", "a")]
    if include_wanted:
        params.append(("vat", "v"))
    optional = {
        "k": keyword,
        "vapi": min_price,
        "vapa": max_price,
        "val": near,
        "vadm": max_distance_km,
        "vami": min_seller_rating,
    }
    params += [(key, str(value)) for key, value in optional.items() if value is not None and value != ""]
    params += [("vaps", _CONDITIONS[condition]) for condition in conditions or []]
    if seller_type:
        params.append(("vast", _SELLER_TYPES[seller_type]))
    field, direction = _SORTS[sort]
    params += [("orderField", field), ("orderSpecId", "-1"), ("orderSort", direction)]
    if page > 1:
        params.append(("page", str(page)))
    return params
