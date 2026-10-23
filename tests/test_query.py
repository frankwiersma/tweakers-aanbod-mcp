import pytest

from tweakers_aanbod_mcp.query import search_params


def test_defaults_ask_for_offers_sorted_newest_first():
    assert search_params() == [("vat", "a"), ("orderField", "time"), ("orderSpecId", "-1"), ("orderSort", "desc")]


def test_filters_map_to_tweakers_parameters():
    params = search_params(
        keyword="thinkpad",
        min_price=150,
        max_price=400,
        near="Utrecht",
        max_distance_km=30,
        conditions=["good", "visibly_used"],
        seller_type="business",
        min_seller_rating=4,
        sort="nearest",
        page=2,
        include_wanted=True,
    )

    assert params == [
        ("vat", "a"),
        ("vat", "v"),
        ("k", "thinkpad"),
        ("vapi", "150"),
        ("vapa", "400"),
        ("val", "Utrecht"),
        ("vadm", "30"),
        ("vami", "4"),
        ("vaps", "goede staat"),
        ("vaps", "gebruikssporen"),
        ("vast", "business"),
        ("orderField", "distance"),
        ("orderSpecId", "-1"),
        ("orderSort", "asc"),
        ("page", "2"),
    ]


@pytest.mark.parametrize(
    "kwargs",
    [{"sort": "nearest"}, {"max_distance_km": 10}, {"min_seller_rating": 6}],
)
def test_rejects_inconsistent_filters(kwargs):
    with pytest.raises(ValueError):
        search_params(**kwargs)
