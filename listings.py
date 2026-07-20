"""
Formats a raw shop-item payload (from either Depop or Vinted) into draft
fields for the *other* marketplace. Nothing here writes to Depop or Vinted -
it's a copy/paste assistant, not an automation bot.

The actual fetch happens in the user's own browser (see the bookmarklets
built in app.py), not on this server - Depop's Cloudflare bot management
blocks server-to-server requests regardless of cookie validity, and
Vinted's per-user closet listing is client-rendered and never appears in a
plain server-side fetch either. A real browser session is required either
way, so this module only ever sees data the bookmarklet already extracted.

VERIFY BEFORE RELYING ON THIS: both marketplaces can change their page
structure without notice. If fields come back empty, open a listing in a
browser, check DevTools, and update the relevant bookmarklet in app.py.
"""

from __future__ import annotations


def format_listing(item: dict) -> dict:
    price = item.get("price") or {}
    pictures = item.get("pictures") or []
    photos = [p.get("originalUrl") or p.get("url") for p in pictures if isinstance(p, dict)]
    brand = item.get("brand")
    if isinstance(brand, dict):
        brand = brand.get("name")

    return {
        "id": str(item.get("id") or item.get("slug") or ""),
        "url": item.get("url") or f"https://www.depop.com/products/{item.get('slug', '')}",
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
