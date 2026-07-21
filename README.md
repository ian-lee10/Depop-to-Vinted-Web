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
3. Click the bookmark. It immediately opens a second tab that fills in
   live as it goes: a progress bar, then each listing's draft card as
   it's read - photos, description, and a copy button next to every
   individual field (price, brand, size, condition) so you can paste
   each straight into the matching field on the other site's listing
   form, rather than one big block you'd have to split apart yourself.
   Your Depop tab is left untouched throughout.

**Vinted → Depop**
1. Drag the "Vinted to Depop" bookmarklet to your bookmarks bar.
2. Go to **your own Vinted closet page** (your profile — the page showing
   your listing grid).
3. Click the bookmark. Same idea: a live-updating tab opens immediately,
   filling in with Depop-ready drafts as each item is read.

### Prefer a one-click button? Use the extension

The bookmarklet's drag-to-bookmarks-bar step trips up a lot of people. The
`extension/` folder is a Chrome/Edge extension that does the exact same
thing as a toolbar button — no bookmarks bar needed. Load it unpacked in
seconds, or publish it to the Chrome Web Store. See
[extension/README.md](extension/README.md).

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
read with a plain server-side request - Depop's Cloudflare bot management
blocks server-to-server requests to their internal API
(`webapi.depop.com`) regardless of cookie validity (confirmed: it returns a
Cloudflare bot-management block page, not an app-level error), and that
same API has no CORS allowance for browser-side calls either (confirmed
via a live console error). So both bookmarklets run from the user's own
browser instead, but the two directions found very different underlying
mechanisms:

- **Depop**: the shop grid is server-rendered but only exposes prices and
  links, so the bookmarklet reads the grid from the live DOM (scrolling
  first, since it lazy-loads more items as you scroll), then fetches each
  product's own page **one at a time** (same-origin, no CORS) and parses
  title/description text, the brand attribute link, and photos with
  `DOMParser`, using CSS-module class-name substrings since Depop's product
  pages don't expose clean structured data.
- **Vinted**: the closet grid turned out to be backed by a clean, same-
  origin JSON API the page itself calls -
  `/api/v2/wardrobe/<user_id>/items?page=N&per_page=50` - found by
  inspecting the page's own network requests. The bookmarklet pages through
  that directly (looping until a page comes back short) rather than
  scrolling and scraping the DOM, which gets a complete, accurate item
  count with clean brand/size/condition/price/photos fields already
  structured - no more guessing when scroll-based lazy-loading is "done."
  It still fetches each item's own page once (throttled, same as Depop) to
  pull the fuller free-text description via a
  `<script type="application/ld+json">` Product block, since the wardrobe
  API only returns the short title.

  This API call has been observed returning a 403 for at least one real,
  logged-in session while working fine anonymously for the same account -
  looks like a stricter anti-bot/CSRF check for authenticated requests, not
  reproducible on demand. Rather than chase that further, the Vinted
  bookmarklet tries the wardrobe API first and, if it fails for any reason,
  falls back to the same scroll-and-scrape-the-DOM approach Depop uses
  (`runViaDomScraping` in `VINTED_BOOKMARKLET_TEMPLATE`) - slower and
  without the API's cleaner size/condition data, but it keeps working when
  the API path doesn't.

As each item is read, the bookmarklet `postMessage`s it to a window it
opened at the very start (synchronously, in direct response to the click,
so popup blockers allow it) - that window, served at `/progress`, renders
each draft live as it arrives with a working copy button. The server never
talks to either marketplace and never sees the scraped data at all beyond
serving that one static-ish page; everything after the initial load is
pure client-side rendering in the browser.

The one-at-a-time throttling on the per-item description fetches matters:
firing every request at once (`Promise.all`) is a big enough burst to trip
rate limiting on either site (hit this myself testing against Vinted) -
when that happens the fetched page is a block page with no product data,
so Depop's extractor returns `null` rather than a fake zeroed-out listing
when the expected data isn't there (Vinted's already has everything it
needs from the wardrobe API regardless of whether the description fetch
succeeds).

## What's not available

- **Depop → Vinted**: condition isn't exposed as structured data on Depop's
  product pages at all — left blank. Size is usually spelled out in the
  seller's own title text ("size medium", "size XL"), so it's pulled out
  with a best-effort regex — not always present. Brand is blank for items
  Depop categorizes as "Other"/unbranded — that reflects Depop's own data,
  not a scraping gap.
- **Vinted → Depop**: size, condition, and brand come from Vinted's own
  wardrobe API fields, so these are reliably populated whenever the seller
  set them. If the per-item description fetch fails for a given listing
  (e.g. rate-limited), the draft falls back to just the title rather than
  dropping the listing entirely - the wardrobe API already has everything
  else.

## Why this design

- **No automation on either marketplace** — sidesteps both sites'
  anti-bot/ToS concerns entirely by never logging into or writing to
  either one programmatically.
- **No credentials involved at all** — nothing here ever sees a password or
  session cookie for either site; it only reads pages that are public
  anyway.
- **Nothing for the server to abuse** — since results are rendered
  entirely client-side from data the bookmarklet already extracted, there's
  no endpoint that accepts arbitrary scraped data and processes it
  server-side.

## If either marketplace changes its page layout

The scraping logic for both directions lives in `app.py`, in
`DEPOP_BOOKMARKLET_TEMPLATE` and `VINTED_BOOKMARKLET_TEMPLATE`:

- Depop: CSS-module class-name substrings (`linkAttribute`, `textWrapper`)
  and the `/P<n>.jpg` product-photo filename pattern.
- Vinted: the `/api/v2/wardrobe/<user_id>/items` response shape (title,
  brand, size, status, price, photos) and, for the fuller description, the
  `application/ld+json` Product block on each item's own page.

These are the most likely things to break if either site ships a redesign.
The card-rendering logic (title/draft-text assembly, copy button) lives in
`templates/progress.html`'s `<script>` block and expects the flat item
shape both bookmarklets already extract: `{url, description, price,
currency, brand, size, condition, photos}`.
