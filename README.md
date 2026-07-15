# Depop → Vinted draft assistant

A small Flask site that reads your active Depop listings and formats each one
as copy/paste-ready text (title, description, price, brand, size, condition)
plus photo links — so you can paste it into a new Vinted listing yourself.

**It does not touch Vinted at all, and it does not post anything to Depop.**
It's a formatter, not a bot.

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5050.

## Using it

The homepage gives you a bookmarklet to drag to your bookmarks bar. Click it
while you're logged into depop.com, and it fetches your listings *from your
own browser tab* and opens a new tab here with the formatted drafts.

Depop has no public developer API, and their Cloudflare bot management
blocks this kind of request when it comes from a server rather than a real
logged-in browser session — so the fetch has to run client-side. This app's
server never talks to Depop at all; it only receives the already-fetched
JSON from the bookmarklet and formats it.

## Why this design

- **No Vinted automation** — sidesteps Vinted's anti-bot/ToS concerns
  entirely by never logging into or writing to Vinted programmatically.
- **No server-side credential handling** — your Depop session cookie never
  leaves your browser; the bookmarklet's `fetch()` call uses it directly,
  and only the resulting product JSON (not the cookie) is sent here.
- **Not hardened for high-volume public hosting** — the `/from-browser`
  endpoint has a basic per-IP rate limit and a request-size cap, but no
  auth. Fine for a personal tool shared with friends; add real rate
  limiting/auth in front of it before pointing serious traffic at it.

## If Depop changes its API

`depop.py::format_listing` assumes a particular JSON shape for each product
(price, pictures, brand, etc.) - Depop can change this without notice. If
fields come back empty, open a Depop shop page, check DevTools → Network for
the `/shop/<user>/products/` response shape, and update the field names in
`depop.py::format_listing` to match. `test_depop.py` has a self-check you can
run after changing it: `python test_depop.py`.
