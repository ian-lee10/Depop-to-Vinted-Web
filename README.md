# Depop ⇄ Vinted draft assistant

**Live: https://depop-to-vinted-web.onrender.com**

Reads your active listings on one marketplace and formats each one as
copy/paste-ready text (title, description, price, brand, size, condition)
plus photo links — so you can paste it into a new listing on the other.
Works **both directions**: Depop → Vinted and Vinted → Depop.

**No login. No cookie. No automation on either site.** It only reads public
shop/closet pages and never writes to either marketplace.

## Using it

The [live site](https://depop-to-vinted-web.onrender.com) gives you two
bookmarklets, one per direction:

**Depop → Vinted**
1. Drag the "Depop to Vinted" bookmarklet to your bookmarks bar.
2. Go to **your own Depop shop page** (`depop.com/yourusername` — the page
   showing your listing grid).
3. Click the bookmark. It scrolls through your shop to pick up every
   listing, reads each product's own page, and shows the formatted drafts
   right in that tab.

**Vinted → Depop**
1. Drag the "Vinted to Depop" bookmarklet to your bookmarks bar.
2. Go to **your own Vinted closet page** (your profile — the page showing
   your listing grid).
3. Click the bookmark. Same idea: scrolls, reads each item's page, shows
   Depop-ready drafts in that tab.

## Run it locally

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5050 — both bookmarklets it generates point at
whatever host is serving the page, so a locally-run copy gives you
bookmarklets wired to `localhost`.

## How it actually works

Neither Depop nor Vinted has a public developer API, and neither can be
read with a plain server-side request:

- Depop's Cloudflare bot management blocks server-to-server requests to
  their internal API (`webapi.depop.com`) regardless of cookie validity —
  confirmed: it returns a Cloudflare bot-management block page, not an
  app-level error. That same API also has no CORS allowance for
  browser-side calls either — confirmed via a live console error when
  called from an actual depop.com page.
- Vinted's per-seller closet grid is rendered client-side only — a plain
  `fetch()` of the profile URL returns zero item links, confirmed by
  comparing the raw response against the live, hydrated page.

So both bookmarklets read the shop/closet grid from the already-rendered
live DOM (scrolling first, since both lazy-load more items as you scroll),
then do a same-origin `fetch()` — no CORS involved, same origin as the page
— to each item's own page and parse out the draft fields:

- **Depop**: parses title/description text, the brand attribute link, and
  photos with `DOMParser`, using CSS-module class-name substrings since
  Depop's product pages don't expose clean structured data.
- **Vinted**: reads a `<script type="application/ld+json">` Product block
  (name, description, price, brand) plus `data-testid="item-attributes-*"`
  fields for size/condition — much cleaner structured data than Depop's.

The server side (`/from-browser`) never talks to either marketplace — it
only receives the already-extracted data from whichever bookmarklet ran and
formats it for display.

## What's not available

- **Depop → Vinted**: condition isn't exposed as structured data on Depop's
  product pages at all — left blank. Size is usually spelled out in the
  seller's own title text ("size medium", "size XL"), so it's pulled out
  with a best-effort regex — not always present. Brand is blank for items
  Depop categorizes as "Other"/unbranded — that reflects Depop's own data,
  not a scraping gap.
- **Vinted → Depop**: size, condition, and brand come from Vinted's own
  structured fields, so these are reliably populated whenever the seller
  set them.

## Why this design

- **No automation on either marketplace** — sidesteps both sites'
  anti-bot/ToS concerns entirely by never logging into or writing to
  either one programmatically.
- **No credentials involved at all** — nothing here ever sees a password or
  session cookie for either site; it only reads pages that are public
  anyway.
- **Not hardened for high-volume public hosting** — `/from-browser` has a
  basic per-IP rate limit and a request-size cap, but no auth. Fine for a
  personal tool shared with friends; add real rate limiting/auth in front
  of it before pointing serious traffic at it.

## If either marketplace changes its page layout

The scraping logic for both directions lives in `app.py`, in
`DEPOP_BOOKMARKLET_TEMPLATE` and `VINTED_BOOKMARKLET_TEMPLATE`:

- Depop: CSS-module class-name substrings (`linkAttribute`, `textWrapper`)
  and the `/P<n>.jpg` product-photo filename pattern.
- Vinted: the `application/ld+json` Product block and the
  `data-testid="item-attributes-*"` selectors.

These are the most likely things to break if either site ships a redesign.
`listings.py::format_listing` just reshapes whatever the relevant
bookmarklet already extracted, regardless of source; `test_listings.py` has
a self-check to run after changing either bookmarklet or `format_listing`:
`python test_listings.py`.
