"""Runnable self-check for depop.py. Run: python test_depop.py"""

from depop import format_listing, parse_shop_response

SAMPLE_ITEM = {
    "id": 123,
    "slug": "abc123-vintage-jacket",
    "description": "Vintage denim jacket\nWorn twice, great condition",
    "price": {"priceAmount": 25.5, "currencyIsoCode": "GBP"},
    "brand": {"name": "Levi's"},
    "size": "M",
    "condition": "Used - excellent",
    "pictures": [{"originalUrl": "https://example.com/1.jpg"}, {"url": "https://example.com/2.jpg"}],
}


def test_format_listing():
    result = format_listing(SAMPLE_ITEM)
    assert result["title"] == "Vintage denim jacket"
    assert result["description"] == SAMPLE_ITEM["description"]
    assert result["price"] == 25.5
    assert result["currency"] == "GBP"
    assert result["brand"] == "Levi's"
    assert result["size"] == "M"
    assert result["photos"] == ["https://example.com/1.jpg", "https://example.com/2.jpg"]
    assert result["url"] == "https://www.depop.com/products/abc123-vintage-jacket"


def test_format_listing_missing_fields():
    result = format_listing({"id": 1})
    assert result["title"] == "(untitled)"
    assert result["photos"] == []
    assert result["price"] is None


def test_parse_shop_response_dict_shape():
    items = parse_shop_response({"products": [SAMPLE_ITEM]})
    assert len(items) == 1
    assert items[0]["title"] == "Vintage denim jacket"


def test_parse_shop_response_list_shape():
    items = parse_shop_response([SAMPLE_ITEM, {"id": 1}])
    assert len(items) == 2


def test_parse_shop_response_garbage():
    assert parse_shop_response({}) == []
    assert parse_shop_response({"products": "not-a-list"}) == []
    assert parse_shop_response([1, "x", None, SAMPLE_ITEM]) == [format_listing(SAMPLE_ITEM)]


if __name__ == "__main__":
    test_format_listing()
    test_format_listing_missing_fields()
    test_parse_shop_response_dict_shape()
    test_parse_shop_response_list_shape()
    test_parse_shop_response_garbage()
    print("ok")
