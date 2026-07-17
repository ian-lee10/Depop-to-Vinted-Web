# Depop → Vinted draft assistant

**Live: https://depop-to-vinted-web.onrender.com**

Reads your active Depop listings and formats each one as copy/paste-ready
text (title, description, price, brand, size where the seller spelled it
out) plus photo links — so you can paste it into a new Vinted listing
yourself.

**No login. No cookie. No Vinted automation.** It only reads Depop's public
shop/product pages and never touches Vinted at all.

## Using it

1. Go to the [live site](https://depop-to-vinted-web.onrender.com) and drag
   the bookmarklet to your bookmarks bar.
2. Go to **your own Depop shop page** (`depop.com/yourusername` — the page
   showing your listing grid).
3. Click the bookmark. It scrolls through your shop to pick up every
   listing, reads each product's own page, and shows the formatted drafts
   right in that tab.

## Run it locally

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5050 — the bookmarklet it generates points at
whatever host is serving the page, so a locally-run copy gives you a
bookmarklet wired to `localhost`.

## How it actually works

Depop has no public developer API. Two things ruled out the obvious
approaches:

- Their Cloudflare bot management blocks server-to-server requests to their
  internal API (`webapi.depop.com`) regardless of cookie validity —
  confirmed: it returns a Cloudflare bot-management block page, not an
  app-level error.
- That same API also has no CORS allowance for browser-side calls either —
  confirmed via a live console error when called from an actual depop.com
  page.

So instead, this reads Depop's own public, server-rendered HTML: the
bookmarklet runs on your shop page, scrolls to load every listing (Depop
lazy-loads the grid), then does a same-origin `fetch()` to each product's
own page and parses out title/description/brand/price/photos with
`DOMParser`. Same-origin fetches aren't subject to CORS at all, and
shop/product pages are public — no login or cookie needed anywhere in this.

The server side (`/from-browser`) never talks to Depop — it only receives
the already-extracted data from the bookmarklet and formats it for display.

## What's not available

- **Condition** isn't exposed as structured data on these pages at all —
  left blank.
- **Size** is usually spelled out in the seller's own title text ("size
  medium", "size XL"), so it's pulled out with a best-effort regex — not
  always present if the seller didn't write it that way.
- **Brand** is blank for items Depop categorizes as "Other"/unbranded —
  that reflects Depop's own data, not a scraping gap.

## Why this design

- **No Vinted automation** — sidesteps Vinted's anti-bot/ToS concerns
  entirely by never logging into or writing to Vinted programmatically.
- **No credentials involved at all** — nothing here ever sees a Depop
  password or session cookie; it only reads pages that are public anyway.
- **Not hardened for high-volume public hosting** — `/from-browser` has a
  basic per-IP rate limit and a request-size cap, but no auth. Fine for a
  personal tool shared with friends; add real rate limiting/auth in front
  of it before pointing serious traffic at it.

## If Depop changes its page layout

The scraping selectors live in `app.py`'s `BOOKMARKLET_TEMPLATE` — mainly
CSS-module class-name substrings (`linkAttribute`, `textWrapper`) and the
`/P<n>.jpg` product-photo filename pattern. These are the most likely
things to break if Depop ships a redesign. `depop.py::format_listing` just
reshapes whatever the bookmarklet already extracted; `test_depop.py` has a
self-check to run after changing either: `python test_depop.py`.
