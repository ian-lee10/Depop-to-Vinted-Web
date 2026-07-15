"""Runnable self-check for depop.format_listing. Run: python test_depop.py"""

from depop import format_listing

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


if __name__ == "__main__":
    test_format_listing()
    test_format_listing_missing_fields()
    print("ok")
