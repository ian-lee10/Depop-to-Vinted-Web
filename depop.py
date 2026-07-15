"""
Read-only fetch from Depop's unofficial web API, formatted into Vinted-ready
draft fields. Nothing here writes to Depop or Vinted - it's a copy/paste
assistant, not an automation bot.

Depop has no public developer API; this hits the same endpoint their own
web app uses and requires the caller's own logged-in session cookie.

VERIFY BEFORE RELYING ON THIS: Depop can change response shapes without
notice. If fields come back empty, open a shop page in a browser, check
DevTools -> Network -> the /shop/<user>/products/ request, and update the
key names below to match.
"""

from __future__ import annotations

import requests

BASE_URL = "https://webapi.depop.com/api/v2"
SHOP_ITEMS_PATH = "/shop/{username}/products/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}


def format_listing(item: dict) -> dict:
    price = item.get("price") or {}
    # VERIFY: photo key seen in the wild as "pictures"; Depop has changed this before.
    pictures = item.get("pictures") or []
    photos = [p.get("originalUrl") or p.get("url") for p in pictures if isinstance(p, dict)]
    brand = item.get("brand")
    if isinstance(brand, dict):
        brand = brand.get("name")

    return {
        "id": str(item.get("id") or item.get("slug") or ""),
        "url": f"https://www.depop.com/products/{item.get('slug', '')}",
        "title": (item.get("description") or "").split("\n")[0][:80] or "(untitled)",
        "description": item.get("description", ""),
        "price": price.get("priceAmount"),
        "currency": price.get("currencyIsoCode") or price.get("currency") or "",
        "brand": brand or "",
        "size": item.get("size") or "",
        "condition": item.get("condition") or "",
        "photos": [p for p in photos if p],
    }


def fetch_listings(username: str, cookie: str) -> list[dict]:
    """Read-only. Requires the caller's own Depop session cookie - never stored."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["Cookie"] = cookie
    resp = session.get(BASE_URL + SHOP_ITEMS_PATH.format(username=username), timeout=20)
    resp.raise_for_status()
    data = resp.json()
    raw_items = data.get("products", data if isinstance(data, list) else [])
    return [format_listing(item) for item in raw_items]
