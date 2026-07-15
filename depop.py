"""
Formats a raw Depop shop-products API response into Vinted-ready draft
fields. Nothing here writes to Depop or Vinted - it's a copy/paste
assistant, not an automation bot.

The actual fetch from Depop's unofficial web API happens in the user's own
browser (see the bookmarklet built in app.py), not on this server - Depop's
Cloudflare bot management blocks server-to-server requests to
webapi.depop.com regardless of cookie validity, so a real browser session
is the only thing that gets through.

VERIFY BEFORE RELYING ON THIS: Depop can change response shapes without
notice. If fields come back empty, open a shop page in a browser, check
DevTools -> Network -> the /shop/<user>/products/ request, and update the
key names below to match.
"""

from __future__ import annotations


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


def parse_shop_response(payload: dict | list) -> list[dict]:
    raw_items = payload.get("products", payload if isinstance(payload, list) else []) if isinstance(payload, dict) else payload
    if not isinstance(raw_items, list):
        raw_items = []
    return [format_listing(item) for item in raw_items if isinstance(item, dict)]
